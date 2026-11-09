import { Redirect } from "expo-router";
import { Loading, Screen } from "@/ui";
import { useSession } from "@/session";

export default function Index() {
  const { ready, me } = useSession();
  if (!ready) {
    return (
      <Screen>
        <Loading />
      </Screen>
    );
  }
  return <Redirect href={me ? "/feed" : "/login"} />;
}
