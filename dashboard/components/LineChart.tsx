"use client";
import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

type Props = {
  labels: string[];
  series: { label: string; data: number[]; color: string }[];
};

export default function LineChart({ labels, series }: Props) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    if (chartRef.current) {
      chartRef.current.destroy();
      chartRef.current = null;
    }
    const ctx = ref.current.getContext("2d");
    if (!ctx) return;
    chartRef.current = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: series.map((s) => ({
          label: s.label,
          data: s.data,
          borderColor: s.color,
          backgroundColor: s.color,
          fill: false,
          tension: 0.3,
        })),
      },
      options: {
        plugins: {
          legend: { labels: { color: "#e5e7eb" } },
          tooltip: { enabled: true },
        },
        scales: {
          x: { ticks: { color: "#9ca3af" }, grid: { color: "#1f2937" } },
          y: { ticks: { color: "#9ca3af" }, grid: { color: "#1f2937" } },
        },
      },
    });
    return () => {
      chartRef.current?.destroy();
    };
  }, [labels.join("|"), JSON.stringify(series)]);

  return <canvas ref={ref} style={{ width: "100%", height: 280 }} />;
}


