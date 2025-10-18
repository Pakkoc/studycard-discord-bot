"use client";
import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

type Cell = { dow: number; hour: number; count: number };

type Props = {
  data: Cell[];
};

// Renders a 7x24 heatmap using Chart.js matrix-like rendering via bar chart with category scales
export default function Heatmap({ data }: Props) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    chartRef.current?.destroy();
    const ctx = ref.current.getContext("2d");
    if (!ctx) return;

    const labelsX = Array.from({ length: 24 }, (_, h) => `${h}:00`);
    const labelsY = ["일", "월", "화", "수", "목", "금", "토"]; // dow 0..6

    // Build 7*24 grid values; map count to intensity
    const grid: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0));
    for (const c of data) {
      const d = Math.max(0, Math.min(6, c.dow));
      const h = Math.max(0, Math.min(23, c.hour));
      grid[d][h] = c.count;
    }
    const flatValues: number[] = grid.flat();
    const max = Math.max(1, ...flatValues);

    // We render as a bar chart with stacked datasets per DOW
    const datasets = labelsY.map((_, dow) => ({
      label: `dow-${dow}`,
      data: grid[dow].map((v) => v || 0),
      backgroundColor: grid[dow].map((v) => intensityColor(v / max)),
      stack: "heat",
      borderWidth: 0,
      barPercentage: 1,
      categoryPercentage: 1,
    }));

    chartRef.current = new Chart(ctx, {
      type: "bar",
      data: { labels: labelsX, datasets },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: {
          x: { stacked: true, ticks: { color: "#6b7280" }, grid: { color: "#e5e7eb" } },
          y: {
            stacked: true,
            ticks: {
              color: "#6b7280",
              callback: (v: any) => labelsY[Number(v)] ?? String(v),
            },
            grid: { color: "#e5e7eb" },
          },
        },
      },
    });

    return () => chartRef.current?.destroy();
  }, [JSON.stringify(data)]);

  return <div style={{ width: "100%", height: 280 }}><canvas ref={ref} /></div>;
}

function intensityColor(t: number) {
  // t in [0,1] -> light blue to dark blue
  const clamped = Math.max(0, Math.min(1, t));
  const start = { r: 219, g: 234, b: 254 }; // blue-100
  const end = { r: 37, g: 99, b: 235 }; // blue-600
  const r = Math.round(start.r + (end.r - start.r) * clamped);
  const g = Math.round(start.g + (end.g - start.g) * clamped);
  const b = Math.round(start.b + (end.b - start.b) * clamped);
  return `rgb(${r}, ${g}, ${b})`;
}


