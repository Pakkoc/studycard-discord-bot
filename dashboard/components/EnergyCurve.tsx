"use client";
import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

type Props = {
  labels: string[]; // 0..23
  data: number[];   // normalized or raw seconds; component normalizes to %
  label?: string;
};

export default function EnergyCurve({ labels, data, label = "에너지" }: Props) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    chartRef.current?.destroy();
    const ctx = ref.current.getContext("2d");
    if (!ctx) return;

    const sum = data.reduce((a, b) => a + (b || 0), 0) || 1;
    const pct = data.map((v) => Math.round(((v || 0) / sum) * 1000) / 10); // 0.1% 단위

    chartRef.current = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label,
            data: pct,
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59,130,246,0.25)",
            fill: true,
            tension: 0.4,
            pointRadius: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: "#111827" } },
          tooltip: { enabled: true, callbacks: { label: (ctx) => `${ctx.parsed.y}%` } },
        },
        scales: {
          x: { ticks: { color: "#6b7280" }, grid: { color: "#e5e7eb" } },
          y: { ticks: { color: "#6b7280", callback: (v) => `${v}%` }, grid: { color: "#e5e7eb" }, beginAtZero: true, suggestedMin: 0 },
        },
      },
    });

    return () => chartRef.current?.destroy();
  }, [labels.join("|"), data.join(","), label]);

  return <div style={{ width: "100%", height: 240 }}><canvas ref={ref} /></div>;
}


