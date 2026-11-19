import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Cpu, Database, RefreshCw, Server, Sparkles, XCircle } from "lucide-react";
import { useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient, BACKEND_ORIGIN } from "@/lib/api-client";
import { warmupBackend } from "@/lib/warmup";

export function HomePage() {
  useEffect(() => {
    warmupBackend();
  }, []);

  const readyQuery = useQuery({
    queryKey: ["system-ready"],
    queryFn: apiClient.getReady,
    refetchOnWindowFocus: false,
  });

  const storefrontQuery = useQuery({
    queryKey: ["storefront-overview"],
    queryFn: apiClient.getStorefront,
    refetchOnWindowFocus: false,
  });

  const ready = readyQuery.data;
  const storefront = storefrontQuery.data;
  const isChecking = readyQuery.isFetching || storefrontQuery.isFetching;

  const pgReady = Boolean(
    ready?.postgresql.connected && ready.postgresql.missing_extensions.length === 0
  );
  const ollamaReady = Boolean(ready?.ollama.connected);

  return (
    <div className="mx-auto max-w-6xl space-y-10 px-4 py-12 sm:px-6">
      <section className="rounded-2xl border bg-gradient-to-br from-secondary/80 via-card to-background p-8 shadow-sm sm:p-12">
        <div className="max-w-3xl space-y-4">
          <Badge variant="secondary" className="gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            Giai đoạn P0 · Local-First (No-Docker) Walking Skeleton
          </Badge>
          <h1 className="font-serif text-3xl font-bold tracking-tight text-foreground sm:text-5xl">
            {storefront?.brand_name ?? "BREW & BEAN"} —{" "}
            <span className="text-primary">Nghệ thuật Cà phê &amp; Bean AI</span>
          </h1>
          <p className="text-base text-muted-foreground sm:text-lg">
            {storefront?.tagline_vi ??
              "Khám phá hương vị Arabica Cầu Đất, Robusta Buôn Ma Thuột và trò chuyện trực tiếp cùng trợ lý Bean AI Barista."}
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              onClick={() => {
                void readyQuery.refetch();
                void storefrontQuery.refetch();
              }}
              disabled={isChecking}
            >
              <RefreshCw className={`h-4 w-4 ${isChecking ? "animate-spin" : ""}`} />
              {isChecking ? "Đang kiểm tra kết nối..." : "Kiểm tra lại kết nối /ready"}
            </Button>
            <span className="text-xs text-muted-foreground">
              Backend: <code>{BACKEND_ORIGIN}/ready</code>
            </span>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">
              Trạng thái hạ tầng Local Native (Không dùng Docker)
            </h2>
            <p className="text-sm text-muted-foreground">
              Kiểm chứng kết nối thông suốt giữa React (5173) → FastAPI (8000) → PostgreSQL 17 &amp;
              Ollama Local (11434).
            </p>
          </div>
          {ready && (
            <Badge variant={ready.ready && ollamaReady ? "success" : "warning"}>
              {ready.ready && ollamaReady
                ? "P0 Ready · Online Full AI"
                : `Status: ${ready.status} (${ready.ai_mode})`}
            </Badge>
          )}
        </div>

        {readyQuery.isError && (
          <Card className="border-red-300 bg-red-50/70">
            <CardContent className="flex items-center gap-3 pt-6 text-sm text-red-800">
              <XCircle className="h-5 w-5 shrink-0" />
              <span>
                Không kết nối được tới FastAPI tại <code>{BACKEND_ORIGIN}/ready</code>:{" "}
                {readyQuery.error instanceof Error ? readyQuery.error.message : "Unknown error"}
              </span>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-5 md:grid-cols-3">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <Server className="h-5 w-5 text-primary" />
                <Badge variant={ready ? "success" : "outline"}>
                  {ready ? "Connected" : "Checking"}
                </Badge>
              </div>
              <CardTitle>FastAPI Backend</CardTitle>
              <CardDescription>Python .venv Native · Port 8000</CardDescription>
            </CardHeader>
            <CardContent className="space-y-1.5 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Environment</span>
                <span className="font-medium">{ready?.environment ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Docker Used</span>
                <span className="font-medium">{ready ? String(ready.docker_used) : "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">AI Mode</span>
                <span className="font-medium">{ready?.ai_mode ?? "—"}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <Database className="h-5 w-5 text-primary" />
                <Badge variant={pgReady ? "success" : "destructive"}>
                  {pgReady ? "Ready" : ready ? "Issue" : "Checking"}
                </Badge>
              </div>
              <CardTitle>PostgreSQL 17 + pgvector</CardTitle>
              <CardDescription>Native Windows · localhost:5432</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Database</span>
                <span className="font-medium">{ready?.postgresql.database ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Latency</span>
                <span className="font-medium">
                  {ready ? `${ready.postgresql.latency_ms} ms` : "—"}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {ready &&
                  Object.entries(ready.postgresql.extensions).map(([ext, ver]) => (
                    <Badge key={ext} variant="secondary" className="gap-1 font-mono text-[11px]">
                      <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                      {ext} {ver}
                    </Badge>
                  ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <Cpu className="h-5 w-5 text-primary" />
                <Badge variant={ollamaReady ? "success" : "warning"}>
                  {ollamaReady ? "Online" : ready ? "Offline" : "Checking"}
                </Badge>
              </div>
              <CardTitle>Ollama Local AI Node</CardTitle>
              <CardDescription>127.0.0.1:11434 · Qwen3 + BGE-M3</CardDescription>
            </CardHeader>
            <CardContent className="space-y-1.5 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Version</span>
                <span className="font-medium">{ready?.ollama.version ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">LLM Model</span>
                <span className="font-medium">
                  {ready?.ollama.llm_model ?? "—"}{" "}
                  {ready?.ollama.llm_model_ready ? "✓" : ""}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Embedding</span>
                <span className="font-medium">
                  {ready?.ollama.embedding_model ?? "—"}{" "}
                  {ready?.ollama.embedding_model_ready ? "✓" : ""}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
