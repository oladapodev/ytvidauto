import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.7.1";

const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const KOYEB_API_URL = "https://ytvidauto.koyeb.app";

/**
 * Polls the Koyeb API until the video generation task is completed or failed.
 */
async function pollForCompletion(taskId: string, maxAttempts = 120, intervalMs = 5000): Promise<string> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
            const response = await fetch(`${KOYEB_API_URL}/video/status/${taskId}`, {
                method: "GET",
            });

            if (!response.ok) {
                console.error(`Polling attempt ${attempt + 1} failed with status: ${response.status}`);
                continue;
            }

            const data = await response.json();
            console.log(`Poll attempt ${attempt + 1}: status = ${data.status}`);

            if (data.status === "completed") {
                return `${KOYEB_API_URL}${data.download_url}`;
            }

            if (data.status === "failed") {
                throw new Error(`Video compilation failed: ${data.error_message || "Unknown error"}`);
            }
        } catch (e) {
            console.error("Error during polling iteration:", e.message);
            if (e.message.includes("Video compilation failed")) throw e;
        }

        await new Promise(resolve => setTimeout(resolve, intervalMs));
    }

    throw new Error("Video compilation timed out after maximum attempts");
}

serve(async (req) => {
    if (req.method === "OPTIONS") {
        return new Response("ok", { status: 200, headers: corsHeaders });
    }

    try {
        const authHeader = req.headers.get("Authorization");
        if (!authHeader) {
            return new Response(JSON.stringify({ error: "Missing Authorization header" }), { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } });
        }

        const supabaseAdmin = createClient(
            Deno.env.get("SUPABASE_URL") ?? "",
            Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
        );

        const token = authHeader.replace("Bearer ", "");
        const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(token);

        if (userError || !user) {
            return new Response(JSON.stringify({ error: "Unauthorized", details: userError?.message }), { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } });
        }

        // 2. Parse Body including new timeline_data
        const { projectId, orientation, style, timeline_data } = await req.json();
        if (!projectId) {
            return new Response(JSON.stringify({ error: "Project ID is required" }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } });
        }

        const [{ data: profile }, { data: project }] = await Promise.all([
            supabaseAdmin.from("profiles").select("subscription_tier").eq("user_id", user.id).single(),
            supabaseAdmin.from("projects").select("video_prompts").eq("id", projectId).single()
        ]);

        const allowedTiers = ["starter", "monthly", "quarterly", "biannual", "annual", "pro", "unlimited", "enterprise"];
        if (!profile || !allowedTiers.includes(profile.subscription_tier)) {
            return new Response(JSON.stringify({ error: "Full video compilation requires a paid subscription" }), { status: 403, headers: { ...corsHeaders, "Content-Type": "application/json" } });
        }

        let averageDuration = 5.0;
        if (project?.video_prompts && Array.isArray(project.video_prompts)) {
            const validDurations = project.video_prompts
                .map((p: any) => {
                    const match = p.duration ? p.duration.toString().match(/(\d+(\.\d+)?)/) : null;
                    return match ? parseFloat(match[0]) : null;
                })
                .filter((d: number | null) => d !== null && !isNaN(d));

            if (validDurations.length > 0) {
                averageDuration = validDurations.reduce((a: number, b: number) => a + b, 0) / validDurations.length;
            }
        }

        const { data: images } = await supabaseAdmin
            .from("generated_images")
            .select("scene_number, image_url")
            .eq("project_id", projectId)
            .order("scene_number", { ascending: true });

        const { data: audio } = await supabaseAdmin
            .from("generated_audio")
            .select("audio_url")
            .eq("project_id", projectId)
            .order("created_at", { ascending: false })
            .limit(1)
            .single();

        if (!images || images.length === 0 || !audio) {
            throw new Error("Missing assets for compilation");
        }

        // 5. Prepare Form Data
        const formData = new FormData();
        formData.append("style", (style || 1).toString());
        formData.append("orientation", orientation || "landscape");
        formData.append("image_duration", averageDuration.toString());
        
        // Important: Pass timeline_data if present
        if (timeline_data) {
            formData.append("timeline_data", timeline_data);
        }

        const audioRes = await fetch(audio.audio_url);
        if (!audioRes.ok) throw new Error("Failed to fetch audio");
        formData.append("audio", await audioRes.blob(), "audio.mp3");

        for (const img of images) {
            try {
                const res = await fetch(img.image_url);
                if (res.ok) formData.append("images", await res.blob(), `scene_${img.scene_number}.png`);
            } catch (e) { console.error(e); }
        }

        const koyebResponse = await fetch(`${KOYEB_API_URL}/video/generate-video`, {
            method: "POST",
            body: formData,
        });

        if (!koyebResponse.ok) throw new Error(`Koyeb Error: ${await koyebResponse.text()}`);

        const { task_id: taskId } = await koyebResponse.json();
        const downloadUrl = await pollForCompletion(taskId);

        const finalVideoRes = await fetch(downloadUrl);
        if (!finalVideoRes.ok) throw new Error("Failed to fetch final video");
        
        const videoBuffer = await finalVideoRes.arrayBuffer();
        const storagePath = `${user.id}/${projectId}/final_video_${Date.now()}.mp4`;

        const { error: uploadError } = await supabaseAdmin.storage
            .from("compiled_videos")
            .upload(storagePath, videoBuffer, { contentType: "video/mp4", upsert: true });

        if (uploadError) throw uploadError;

        const { data: { publicUrl: videoUrl } } = supabaseAdmin.storage.from("compiled_videos").getPublicUrl(storagePath);

        await supabaseAdmin.from("compiled_videos").insert({
            project_id: projectId, user_id: user.id, video_url: videoUrl, koyeb_task_id: taskId, status: "completed"
        });

        return new Response(JSON.stringify({ videoUrl, taskId }), { headers: { ...corsHeaders, "Content-Type": "application/json" } });

    } catch (error) {
        return new Response(JSON.stringify({ error: error.message }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }
});