"use client";

import dynamic from "next/dynamic";

// client only: clock, queue and cached roster live in localStorage
export const LiveClient = dynamic(() => import("./live-view").then((m) => m.LiveView), { ssr: false });
