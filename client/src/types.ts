export type Metrics = {
  rsi: number | null;
  pct_from_high: number | null;
  ma200: number | null;
  current_price: number | null;
  peg_ratio: number | null;
  eps_growth_rate: number | null;
  volume_ratio: number | null;
};

export type MarketRegime = {
  above_200ma: boolean | null;
  spy_price: number | null;
  spy_ma200: number | null;
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
  market_regime: MarketRegime;
  verdict: string;
  signals: Signal[];
};

export type HistoryPoint = { date: string; score: number };

export type TickerDetail = {
  signal: Signal;
  history: HistoryPoint[];
};
