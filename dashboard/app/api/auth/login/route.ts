import { cookies } from "next/headers";
import { NextResponse } from "next/server";

// 하드코딩된 관리자 계정
const ADMIN_ID = "admin";
const ADMIN_PW = "admin1234";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { id, password } = body;

    // 아이디/비밀번호 확인
    if (id === ADMIN_ID && password === ADMIN_PW) {
      // 세션 쿠키 설정 (7일간 유효)
      const sessionToken = Buffer.from(`${ADMIN_ID}:${Date.now()}`).toString("base64");

      cookies().set("session", sessionToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 7, // 7일
        path: "/",
      });

      return NextResponse.json({ success: true });
    }

    return NextResponse.json(
      { success: false, message: "아이디 또는 비밀번호가 올바르지 않습니다." },
      { status: 401 }
    );
  } catch {
    return NextResponse.json(
      { success: false, message: "요청 처리 중 오류가 발생했습니다." },
      { status: 500 }
    );
  }
}
