"use client";
import { useEffect, useRef, useState } from "react";
import Chart from "chart.js/auto";

type MemberGrowthPoint = { label: string; newMembers: number; totalMembers: number };

type Props = {
  monthlyData: MemberGrowthPoint[];
  yearlyData: MemberGrowthPoint[];
};

export default function MemberGrowthChart({ monthlyData, yearlyData }: Props) {
  const [period, setPeriod] = useState<"monthly" | "yearly">("monthly");
  const ref = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart | null>(null);

  const data = period === "monthly" ? monthlyData : yearlyData;

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
        labels: data.map((d) => d.label),
        datasets: [
          {
            label: "총 회원수",
            data: data.map((d) => d.totalMembers),
            borderColor: "#60a5fa",
            backgroundColor: "#60a5fa",
            fill: false,
            tension: 0.3,
            pointRadius: 3,
            borderWidth: 2,
            yAxisID: "y",
          },
          {
            label: "신규 가입",
            data: data.map((d) => d.newMembers),
            borderColor: "#34d399",
            backgroundColor: "#34d399",
            fill: false,
            tension: 0.3,
            pointRadius: 3,
            borderWidth: 2,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        plugins: {
          legend: { labels: { color: "#111827" } },
          tooltip: { enabled: true },
        },
        scales: {
          x: { ticks: { color: "#6b7280" }, grid: { color: "#e5e7eb" } },
          y: {
            type: "linear",
            display: true,
            position: "left",
            ticks: { color: "#60a5fa" },
            grid: { color: "#e5e7eb" },
            beginAtZero: false,
            title: { display: true, text: "총 회원수", color: "#60a5fa" },
          },
          y1: {
            type: "linear",
            display: true,
            position: "right",
            ticks: { color: "#34d399" },
            grid: { drawOnChartArea: false },
            beginAtZero: true,
            title: { display: true, text: "신규 가입", color: "#34d399" },
          },
        },
      },
    });

    return () => {
      chartRef.current?.destroy();
    };
  }, [data]);

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button
          onClick={() => setPeriod("monthly")}
          style={{
            padding: "6px 16px",
            borderRadius: 6,
            border: "1px solid #374151",
            background: period === "monthly" ? "#3b82f6" : "#1f2937",
            color: period === "monthly" ? "#fff" : "#9ca3af",
            cursor: "pointer",
            fontWeight: period === "monthly" ? 600 : 400,
            transition: "all 0.15s",
          }}
        >
          월간
        </button>
        <button
          onClick={() => setPeriod("yearly")}
          style={{
            padding: "6px 16px",
            borderRadius: 6,
            border: "1px solid #374151",
            background: period === "yearly" ? "#3b82f6" : "#1f2937",
            color: period === "yearly" ? "#fff" : "#9ca3af",
            cursor: "pointer",
            fontWeight: period === "yearly" ? 600 : 400,
            transition: "all 0.15s",
          }}
        >
          연간
        </button>
      </div>
      <div style={{ position: "relative", height: 220 }}>
        <canvas ref={ref} />
      </div>
    </div>
  );
}
