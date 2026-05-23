export type Metrics = {
  rsi: number | null;
  pct_from_high: number | null;
  ma200: number | null;
  current_price: number | null;
};

export type Signal = {
  ticker: string;
  score: number;
  reasons: string[];
  flags: string[];
  metrics: Metrics;
  error: string | null;
};

export type ScreenPayload = {
  generated_at: string;
  threshold: number;
  verdict: string;
  signals: Signal[];
};

export type HistoryPoint = { date: string; score: number };

export type TickerDetail = {
  signal: Signal;
  history: HistoryPoint[];
};
