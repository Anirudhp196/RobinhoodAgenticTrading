import express, { Request, Response } from "express";
import cors from "cors";
import cron from "node-cron";

const PORT = 3000;
const SCORING_URL = "http://localhost:8000";

const app = express();
app.use(cors());
app.use(express.json());

app.get("/api/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", service: "server" });
});

app.get("/api/scoring-health", async (_req: Request, res: Response) => {
  try {
    const upstream = await fetch(`${SCORING_URL}/health`);
    res.json({ server: "ok", scoring: await upstream.json() });
  } catch (err) {
    res.status(502).json({
      server: "ok",
      scoring: "unreachable",
      error: err instanceof Error ? err.message : String(err),
    });
  }
});

app.get("/api/screen", async (_req: Request, res: Response) => {
  try {
    const upstream = await fetch(`${SCORING_URL}/screen`);
    res.status(upstream.status).json(await upstream.json());
  } catch (err) {
    res.status(502).json({ error: errMsg(err) });
  }
});

app.get("/api/screen/:ticker", async (req: Request, res: Response) => {
  const ticker = encodeURIComponent(String(req.params.ticker));
  try {
    const upstream = await fetch(`${SCORING_URL}/screen/${ticker}`);
    res.status(upstream.status).json(await upstream.json());
  } catch (err) {
    res.status(502).json({ error: errMsg(err) });
  }
});

app.post("/api/refresh", async (_req: Request, res: Response) => {
  try {
    const upstream = await fetch(`${SCORING_URL}/refresh`, { method: "POST" });
    res.status(upstream.status).json(await upstream.json());
  } catch (err) {
    res.status(502).json({ error: errMsg(err) });
  }
});

// Pipe SSE through to the browser.
app.get("/api/stream", async (_req: Request, res: Response) => {
  res.set({
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });
  res.flushHeaders();
  try {
    const upstream = await fetch(`${SCORING_URL}/stream`);
    if (!upstream.body) {
      res.end();
      return;
    }
    const reader = upstream.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      res.write(decoder.decode(value, { stream: true }));
    }
  } catch (err) {
    res.write(`data: ${JSON.stringify({ type: "error", error: errMsg(err) })}\n\n`);
  } finally {
    res.end();
  }
});

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

// Daily refresh: 30 min after US market open (10:00 ET) on weekdays.
// node-cron honors the timezone option so this fires correctly regardless of host TZ.
cron.schedule(
  "0 10 * * 1-5",
  async () => {
    console.log("[cron] running daily refresh");
    try {
      const r = await fetch(`${SCORING_URL}/refresh`, { method: "POST" });
      console.log(`[cron] refresh ${r.ok ? "ok" : `failed ${r.status}`}`);
    } catch (e) {
      console.error("[cron] refresh error:", errMsg(e));
    }
  },
  { timezone: "America/New_York" }
);

app.listen(PORT, () => {
  console.log(`[server] listening on http://localhost:${PORT}`);
  console.log("[server] daily refresh scheduled for 10:00 ET (weekdays)");
});
