"use client";
import { useEffect, useRef } from "react";
import Chart from "chart.js/auto";

type Props = {
  labels: string[]; // e.g., ["0", ..., "23"]
  data: number[];   // length 24
  centerText?: string | number;
};

export default function CircularHeatmap({ labels, data, centerText }: Props) {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    chartRef.current?.destroy();
    const ctx = ref.current.getContext("2d");
    if (!ctx) return;

    const max = Math.max(1, ...data);
    const bg = data.map((v) => intensityColor(v / max));

    // plugin to draw center text
    const centerPlugin = {
      id: "centerText",
      afterDraw(chart: any) {
        if (!centerText) return;
        const { ctx, chartArea } = chart;
        const x = (chartArea.left + chartArea.right) / 2;
        const y = (chartArea.top + chartArea.bottom) / 2;
        ctx.save();
        ctx.fillStyle = "#111827";
        ctx.font = "bold 28px ui-sans-serif, system-ui";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(centerText), x, y);
        ctx.restore();
      },
    } as const;

    chartRef.current = new Chart(ctx, {
      type: "polarArea",
      data: {
        labels,
        datasets: [
          {
            label: "intensity",
            data,
            backgroundColor: bg,
            borderWidth: 1,
            borderColor: "#ffffff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { enabled: true },
        },
        scales: {
          r: {
            ticks: { display: false },
            grid: { color: "#e5e7eb" },
            angleLines: { color: "#e5e7eb" },
          },
        },
      },
      plugins: centerText ? [centerPlugin] : [],
    });

    return () => chartRef.current?.destroy();
  }, [labels.join("|"), data.join(","), String(centerText ?? "")] );

  return <div style={{ width: "100%", height: 260 }}><canvas ref={ref} /></div>;
}

function intensityColor(t: number) {
  const clamped = Math.max(0, Math.min(1, t));
  // light to dark blue scale
  const start = { r: 219, g: 234, b: 254 }; // blue-100
  const end = { r: 37, g: 99, b: 235 }; // blue-600
  const r = Math.round(start.r + (end.r - start.r) * clamped);
  const g = Math.round(start.g + (end.g - start.g) * clamped);
  const b = Math.round(start.b + (end.b - start.b) * clamped);
  return `rgb(${r}, ${g}, ${b})`;
}


