import { useState } from "react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Video, Wand2, Loader2, Download, RefreshCw } from "lucide-react";

interface CompileVideoSectionProps {
    projectId: string;
    projectTitle: string;
    imagePromptsCount: number;
    generatedImagesCount: number;
    audioUrl: string | null;
    compiledVideoUrl: string | null;
    onVideoCompiled: (videoUrl: string) => void;
    timelineData?: any[]; // Pass the timeline from parent state
}

export function CompileVideoSection({
    projectId,
    projectTitle,
    imagePromptsCount,
    generatedImagesCount,
    audioUrl,
    compiledVideoUrl,
    onVideoCompiled,
    timelineData
}: CompileVideoSectionProps) {
    const [isCompilingVideo, setIsCompilingVideo] = useState(false);
    const [compileVideoModalOpen, setCompileVideoModalOpen] = useState(false);
    const [compileOrientation, setCompileOrientation] = useState<"landscape" | "portrait">("landscape");
    const [compileStyle, setCompileStyle] = useState<string>("2"); // Default to Cinematic Pan

    const isReady = generatedImagesCount >= imagePromptsCount && generatedImagesCount > 0 && audioUrl;

    const handleCompileVideoClick = () => {
        setCompileVideoModalOpen(true);
    };

    const confirmCompileVideo = async () => {
        setCompileVideoModalOpen(false);
        if (!projectId) return;

        setIsCompilingVideo(true);
        try {
            const { data: { session } } = await supabase.auth.getSession();

            if (!session?.access_token) {
                throw new Error("Please log in to compile videos");
            }

            const response = await fetch(
                `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/compile-full-video`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${session.access_token}`,
                    },
                    body: JSON.stringify({
                        projectId,
                        orientation: compileOrientation,
                        style: parseInt(compileStyle),
                        timeline_data: timelineData ? JSON.stringify(timelineData) : null
                    }),
                }
            );

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || "Failed to compile video");
            }

            const data = await response.json();
            onVideoCompiled(data.videoUrl);
            toast.success("Full video compilation started! Use the poll URL or check back later.");
        } catch (error) {
            console.error("Video compilation error:", error);
            toast.error(error instanceof Error ? error.message : "Failed to compile video");
        } finally {
            setIsCompilingVideo(false);
        }
    };

    const handleDownload = async () => {
        if (!compiledVideoUrl) return;
        try {
            toast.info("Preparing download...");
            const response = await fetch(compiledVideoUrl);
            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = blobUrl;
            a.download = `${projectTitle.replace(/[^a-z0-9]/gi, "_")}_full_video.mp4`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(blobUrl);
            toast.success("Video downloaded!");
        } catch (error) {
            console.error("Download error:", error);
            toast.error("Failed to download video");
        }
    };

    return (
        <>
            <Card variant="glass" className="border-primary/50">
                <CardHeader>
                    <div className="flex items-center justify-between flex-wrap gap-3">
                        <div>
                            <CardTitle className="flex items-center gap-2">
                                <Video className="w-5 h-5" />
                                Complete Video
                            </CardTitle>
                            <CardDescription>
                                Compile all scenes and audio into a ready-to-publish video
                            </CardDescription>
                        </div>
                        {/* Always show, but disable if not ready */}
                        {!compiledVideoUrl && (
                            <div className="flex flex-col gap-2 items-end">
                                <Button
                                    onClick={handleCompileVideoClick}
                                    disabled={isCompilingVideo || !isReady}
                                    size="lg"
                                    className="gap-2"
                                >
                                    {isCompilingVideo ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Compiling...
                                        </>
                                    ) : (
                                        <>
                                            <Wand2 className="w-4 h-4 mr-2" />
                                            Generate Video
                                        </>
                                    )}
                                </Button>
                                {!isReady && (
                                    <p className="text-xs text-muted-foreground text-right max-w-[200px]">
                                        Generate all {imagePromptsCount} images and audio first.
                                        {(generatedImagesCount < imagePromptsCount) && ` (${generatedImagesCount}/${imagePromptsCount} images ready)`}
                                        {!audioUrl && " (Audio missing)"}
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                </CardHeader>

                {compiledVideoUrl && (
                    <CardContent>
                        <div className="relative rounded-lg overflow-hidden bg-secondary/30">
                            <div className="flex items-center justify-center min-h-[400px] p-4">
                                <video
                                    src={compiledVideoUrl}
                                    controls
                                    className="max-h-[500px] max-w-full rounded-lg shadow-lg"
                                />
                            </div>
                            <div className="flex gap-2 mt-4">
                                <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={handleDownload}
                                >
                                    <Download className="w-4 h-4 mr-2" />
                                    Download Full Video
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleCompileVideoClick}
                                    disabled={isCompilingVideo}
                                >
                                    <RefreshCw className="w-4 h-4 mr-2" />
                                    Regenerate
                                </Button>
                            </div>
                        </div>
                    </CardContent>
                )}
            </Card>

            {/* Full Video Compilation Modal */}
            <Dialog open={compileVideoModalOpen} onOpenChange={setCompileVideoModalOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle>Compile Full Video</DialogTitle>
                        <DialogDescription>
                            Choose the style and format for your final video.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <label htmlFor="orientation" className="text-sm font-medium">
                                Orientation
                            </label>
                            <Select
                                value={compileOrientation}
                                onValueChange={(value: "landscape" | "portrait") => setCompileOrientation(value)}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select orientation" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="landscape">Landscape (16:9)</SelectItem>
                                    <SelectItem value="portrait">Portrait (9:16)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid gap-2">
                            <label htmlFor="style" className="text-sm font-medium">
                                Transition Style
                            </label>
                            <Select value={compileStyle} onValueChange={setCompileStyle}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select style" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="1">Classic Zoom</SelectItem>
                                    <SelectItem value="2">Cinematic Pan</SelectItem>
                                    <SelectItem value="3">Vertical Scroll</SelectItem>
                                    <SelectItem value="4">Static</SelectItem>
                                    <SelectItem value="5">Dynamic Mix</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="secondary" onClick={() => setCompileVideoModalOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={confirmCompileVideo} disabled={isCompilingVideo}>
                            {isCompilingVideo ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Compiling...
                                </>
                            ) : (
                                <>
                                    <Wand2 className="w-4 h-4 mr-2" />
                                    Compile Video
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
