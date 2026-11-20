/**
 * One run of `task` at a time, and none lost: a call while a run is going does not start a second
 * one, but makes the running one go once more when it ends. The courtside marks use it (a tap, the
 * «online» event and the timer must not send the queue twice): a mark tapped while the first
 * upload was still going used to wait for the 15 s timer (e2e 20.11., m11.spec «1 noch nicht
 * hochgeladen»).
 */
export function serial(task: () => Promise<void>): () => Promise<void> {
  let running: Promise<void> | null = null;
  let again = false;
  return () => {
    if (running) {
      again = true;
      return running;
    }
    running = (async () => {
      do {
        again = false;
        await task();
      } while (again);
    })().finally(() => {
      running = null;
    });
    return running;
  };
}
