"use client";
import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

type Props = {
  labels: string[];
  data: number[];
  color?: string;
};

export default function BarChart({ labels, data, color = "#60a5fa" }: Props) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    chartRef.current?.destroy();
    const ctx = ref.current.getContext("2d");
    if (!ctx) return;
    chartRef.current = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{ label: "count", data, backgroundColor: color }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#9ca3af" }, grid: { color: "#1f2937" } },
          y: { ticks: { color: "#9ca3af" }, grid: { color: "#1f2937" } },
        },
      },
    });
    return () => chartRef.current?.destroy();
  }, [labels.join("|"), data.join(",")]);

  return <canvas ref={ref} style={{ width: "100%", height: 260 }} />;
}


