import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  // 세션 쿠키 삭제
  cookies().delete("session");

  // 로그인 페이지로 리다이렉트
  const url = new URL("/login", request.url);
  return NextResponse.redirect(url);
}
