import { level, minutesLeft, preflight, type Level } from "@handball/client-core";
import { useQuery } from "@tanstack/react-query";
import * as Battery from "expo-battery";
import { CameraView, useCameraPermissions, useMicrophonePermissions } from "expo-camera";
import { Paths } from "expo-file-system";
import { useKeepAwake } from "expo-keep-awake";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Accelerometer } from "expo-sensors";
import { useEffect, useRef, useState } from "react";
import { StyleSheet, View } from "react-native";
import { useSession } from "@/session";
import { useTheme } from "@/theme";
import { Body, Button, Card, Screen, Title } from "@/ui";
import { uploadRecording } from "@/upload";

type Match = { id: string; label: string };

/** Phone as camera (5.2): checks, level aid, court frame, recording, upload in parts. */
export default function Record() {
  const { mode } = useLocalSearchParams<{ mode?: string }>();
  const { api, orgId, me, t } = useSession();
  const c = useTheme();
  const router = useRouter();
  const [match, setMatch] = useState<Match | null>(null);
  const teams = useQuery({
    queryKey: ["teams", orgId],
    enabled: !!orgId,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams", { params: { path: { org_id: orgId! } } })).data ?? [],
  });
  const matches = useQuery({
    queryKey: ["upcoming", orgId, teams.data?.length],
    enabled: !!teams.data,
    queryFn: async () => {
      const out: Match[] = [];
      for (const team of teams.data ?? []) {
        const r = await api.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", { params: { path: { org_id: orgId!, team_id: team.id } } });
        for (const m of r.data ?? []) out.push({ id: m.id, label: `${team.name}: ${m.opponent_name} ${new Date(m.kickoff_at).toLocaleDateString()}` });
      }
      return out.slice(0, 12);
    },
  });
  if (!match) {
    return (
      <Screen>
        <Title>{t("chooseMatch")}</Title>
        {(matches.data ?? []).map((m) => (
          <Button key={m.id} kind="secondary" label={m.label} onPress={() => (mode === "marks" ? router.replace(`/marks/${m.id}`) : setMatch(m))} />
        ))}
      </Screen>
    );
  }
  return <Recorder orgId={orgId!} match={match} locale={me?.locale} color={c.accent} />;
}

function Recorder({ orgId, match, color }: { orgId: string; match: Match; locale?: string; color: string }) {
  useKeepAwake();
  const { api, t } = useSession();
  const camera = useRef<CameraView>(null);
  const [cam, askCam] = useCameraPermissions();
  const [mic, askMic] = useMicrophonePermissions();
  const [tilt, setTilt] = useState<Level>("level");
  const [issues, setIssues] = useState<string[]>([]);
  const [free, setFree] = useState(0);
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const freeBytes = Paths.availableDiskSpace;
      setFree(freeBytes);
      const battery = await Battery.getBatteryLevelAsync();
      const state = await Battery.getBatteryStateAsync();
      setIssues(preflight({ freeBytes, batteryLevel: battery < 0 ? null : battery, charging: state === Battery.BatteryState.CHARGING || state === Battery.BatteryState.FULL }));
    })();
    Accelerometer.setUpdateInterval(500);
    const sub = Accelerometer.addListener(({ x, y, z }) => setTilt(level(x, y, z)));
    return () => sub.remove();
  }, []);

  if (!cam?.granted || !mic?.granted) {
    return (
      <Screen>
        <Body>{t("permissionCamera")}</Body>
        <Button label={t("allow")} onPress={() => void askCam().then(() => askMic())} />
      </Screen>
    );
  }

  const start = async () => {
    setRecording(true);
    const result = await camera.current?.recordAsync();
    setRecording(false);
    if (!result?.uri) return;
    setStatus(t("uploading", { percent: 0 }));
    const outcome = await uploadRecording(api, orgId, match.id, result.uri, false, (f) => setStatus(t("uploading", { percent: Math.round(f * 100) })));
    setStatus(outcome === "done" ? t("uploadDone") : outcome === "waiting" ? t("waitingWifi") : t("error"));
  };

  return (
    <View style={{ flex: 1, backgroundColor: "black" }}>
      <CameraView ref={camera} style={StyleSheet.absoluteFill} mode="video" videoQuality="1080p" facing="back" />
      {/* court frame: the whole court should fit inside, goal areas at the edges */}
      <View pointerEvents="none" style={[styles.frame, { borderColor: tilt === "level" ? "#22c55e" : "#f59e0b" }]} />
      <View style={styles.panel}>
        <Card>
          <Body>{t(tilt)} · {t("minutesLeft", { minutes: minutesLeft(free) })}</Body>
          {issues.map((i) => (
            <Body key={i}>{i === "storage" ? t("issue_storage", { minutes: minutesLeft(free) }) : t("issue_battery")}</Body>
          ))}
          {status && <Body>{status}</Body>}
          {!recording && !status && <Body muted>{t("recordHint")}</Body>}
          <Button
            label={recording ? t("stop") : t("start")}
            color={color}
            onPress={() => (recording ? camera.current?.stopRecording() : void start())}
          />
        </Card>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: { position: "absolute", left: "4%", right: "4%", top: "18%", bottom: "18%", borderWidth: 2, borderRadius: 4 },
  panel: { position: "absolute", left: 12, right: 12, bottom: 12 },
});
