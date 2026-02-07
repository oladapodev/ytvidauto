import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.7.1";

const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const KOYEB_API_URL = "https://molecular-janeen-davidson0071-394ced15.koyeb.app";

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
                // The API returns a relative download_url, so we prepend the base URL
                return `${KOYEB_API_URL}${data.download_url}`;
            }

            if (data.status === "failed") {
                throw new Error(`Video compilation failed: ${data.error_message || "Unknown error"}`);
            }
        } catch (e) {
            console.error("Error during polling iteration:", e.message);
            if (e.message.includes("Video compilation failed")) throw e;
        }

        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, intervalMs));
    }

    throw new Error("Video compilation timed out after maximum attempts");
}

serve(async (req) => {
    // Handle CORS preflight
    if (req.method === "OPTIONS") {
        return new Response("ok", { status: 200, headers: corsHeaders });
    }

    try {
        // 1. Authenticate user
        const authHeader = req.headers.get("Authorization");
        if (!authHeader) {
            return new Response(
                JSON.stringify({ error: "Missing Authorization header" }),
                { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
            );
        }

        const supabaseAdmin = createClient(
            Deno.env.get("SUPABASE_URL") ?? "",
            Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
        );

        const token = authHeader.replace("Bearer ", "");
        const { data: { user }, error: userError } = await supabaseAdmin.auth.getUser(token);

        if (userError || !user) {
            console.error("Authentication failed:", userError);
            return new Response(
                JSON.stringify({ error: "Unauthorized", details: userError?.message }),
                { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
            );
        }

        // 2. Get request body
        const { projectId, orientation, style } = await req.json();
        if (!projectId) {
            return new Response(
                JSON.stringify({ error: "Project ID is required" }),
                { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
            );
        }

        // 3. Subscription and Project Data Retrieval
        const [{ data: profile }, { data: project }] = await Promise.all([
            supabaseAdmin
                .from("profiles")
                .select("subscription_tier")
                .eq("user_id", user.id)
                .single(),
            supabaseAdmin
                .from("projects")
                .select("video_prompts")
                .eq("id", projectId)
                .single()
        ]);

        const allowedTiers = ["starter", "monthly", "quarterly", "biannual", "annual", "pro", "unlimited", "enterprise"];
        if (!profile || !allowedTiers.includes(profile.subscription_tier)) {
            return new Response(
                JSON.stringify({ error: "Full video compilation requires a paid subscription" }),
                { status: 403, headers: { ...corsHeaders, "Content-Type": "application/json" } }
            );
        }

        // Calculate average duration for fallback
        let averageDuration = 5.0;
        if (project?.video_prompts && Array.isArray(project.video_prompts)) {
            const validDurations = project.video_prompts
                .map((p: any) => {
                    const match = p.duration ? p.duration.toString().match(/(\d+(\.\d+)?)/) : null;
                    return match ? parseFloat(match[0]) : null;
                })
                .filter((d: number | null) => d !== null && !isNaN(d));

            if (validDurations.length > 0) {
                const total = validDurations.reduce((a: number, b: number) => a + b, 0);
                averageDuration = total / validDurations.length;
            }
        }

        // 4. Fetch Assets
        const { data: images, error: imagesError } = await supabaseAdmin
            .from("generated_images")
            .select("scene_number, image_url")
            .eq("project_id", projectId)
            .order("scene_number", { ascending: true });

        if (imagesError || !images || images.length === 0) {
            throw new Error("No generated images found for this project");
        }

        const { data: audio, error: audioError } = await supabaseAdmin
            .from("generated_audio")
            .select("audio_url")
            .eq("project_id", projectId)
            .order("created_at", { ascending: false })
            .limit(1)
            .single();

        if (audioError || !audio) {
            throw new Error("No generated audio found for this project");
        }

        // 5. Prepare Multipart Form Data
        const formData = new FormData();
        formData.append("style", (style || 1).toString());
        formData.append("orientation", orientation || "landscape");
        formData.append("image_duration", averageDuration.toString());

        // Fetch and append audio binary
        console.log("Downloading audio asset...");
        const audioResponse = await fetch(audio.audio_url);
        if (!audioResponse.ok) throw new Error("Failed to download audio asset from storage");
        const audioBlob = await audioResponse.blob();
        formData.append("audio", audioBlob, "audio.mp3");

        // Fetch and append image binaries
        console.log(`Downloading ${images.length} image assets...`);
        for (const img of images) {
            try {
                const res = await fetch(img.image_url);
                if (res.ok) {
                    const blob = await res.blob();
                    formData.append("images", blob, `scene_${img.scene_number}.png`);
                }
            } catch (e) {
                console.error(`Failed to download image scene ${img.scene_number}:`, e.message);
            }
        }

        // 6. Submit to Koyeb API
        const koyebResponse = await fetch(`${KOYEB_API_URL}/video/generate-video`, {
            method: "POST",
            body: formData,
        });

        if (!koyebResponse.ok) {
            const errorText = await koyebResponse.text();
            throw new Error(`Koyeb submission failed: ${koyebResponse.status} - ${errorText}`);
        }

        const { task_id: taskId } = await koyebResponse.json();
        console.log(`Task created successfully: ${taskId}`);

        // 7. Poll for completion
        const downloadUrl = await pollForCompletion(taskId);
        console.log(`Video generated successfully. Downloading from: ${downloadUrl}`);

        // 8. Download final video and upload to Supabase Storage
        const finalVideoRes = await fetch(downloadUrl);
        if (!finalVideoRes.ok) throw new Error("Failed to download final video from Koyeb");
        
        const videoBuffer = await finalVideoRes.arrayBuffer();
        const storagePath = `${user.id}/${projectId}/final_video_${Date.now()}.mp4`;

        const { error: uploadError } = await supabaseAdmin.storage
            .from("compiled_videos")
            .upload(storagePath, videoBuffer, {
                contentType: "video/mp4",
                upsert: true
            });

        if (uploadError) throw uploadError;

        const { data: { publicUrl: videoUrl } } = supabaseAdmin.storage
            .from("compiled_videos")
            .getPublicUrl(storagePath);

        // 9. Save record to database
        const { error: insertError } = await supabaseAdmin.from("compiled_videos").insert({
            project_id: projectId,
            user_id: user.id,
            video_url: videoUrl,
            koyeb_task_id: taskId,
            status: "completed"
        });

        if (insertError) console.error("Database insert error:", insertError);

        return new Response(
            JSON.stringify({ videoUrl, taskId }),
            { headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );

    } catch (error) {
        console.error("Function Error:", error.message);
        return new Response(
            JSON.stringify({ error: error.message }),
            { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
    }
});
