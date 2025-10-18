"use client";
import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

type Props = {
  labels: string[];
  series: {
    label: string;
    data: number[];
    color: string;
    showLine?: boolean;
    pointRadius?: number | number[];
    borderWidth?: number;
    pointBackgroundColors?: string[];
  }[];
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
          pointBackgroundColor: s.pointBackgroundColors ?? s.color,
          pointRadius: s.pointRadius ?? 2,
          borderWidth: s.borderWidth ?? 2,
        })),
      },
      options: {
        plugins: {
          legend: { labels: { color: "#111827" } },
          tooltip: { enabled: true },
        },
        scales: {
          x: { ticks: { color: "#6b7280" }, grid: { color: "#e5e7eb" } },
          y: { ticks: { color: "#6b7280" }, grid: { color: "#e5e7eb" }, beginAtZero: true, suggestedMin: 0 },
        },
      },
    });
    return () => {
      chartRef.current?.destroy();
    };
  }, [labels.join("|"), JSON.stringify(series)]);

  return <canvas ref={ref} style={{ width: "100%", height: 220 }} />;
}


