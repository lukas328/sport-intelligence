import { afterEach, describe, expect, it, vi } from "vitest";
import { compose, courtToPicture, geometryOf, viewAt, ViewChunks } from "./moving-camera";
import { project, type Homography } from "./spotlight";

const I: Homography = [
  [1, 0, 0],
  [0, 1, 0],
  [0, 0, 1],
];
/** court metres -> hall image px: 20 px per metre, court corner at (100, 50) */
const COURT: Homography = [
  [20, 0, 100],
  [0, 20, 50],
  [0, 0, 1],
];
/** hall image -> frame for a camera that has turned so the hall moved `dx` px to the left */
const shift = (dx: number): Homography => [
  [1, 0, -dx],
  [0, 1, 0],
  [0, 0, 1],
];
function rows(samples: [number, Homography][]): Float32Array {
  return new Float32Array(samples.flatMap(([t, h]) => [t, ...h.flat()]));
}

const analysis = {
  calibration: { homography: COURT, image_size: [1800, 400] },
  chunk_ms: 30000,
  camera: "moving",
  view_chunks: 2,
  frame_size: [640, 360],
  panorama: { width: 1800, height: 400 },
};

describe("geometryOf", () => {
  it("takes a fixed camera's calibration as it is", () => {
    const g = geometryOf({ ...analysis, camera: "fixed", view_chunks: null, frame_size: null }, "/v1/x");
    expect(g).toEqual({ homography: COURT, imageSize: [1800, 400] });
  });

  it("gives a moving camera its view files and the frame they map into", () => {
    expect(geometryOf(analysis, "/v1/orgs/o/videos/v")).toEqual({
      homography: COURT,
      imageSize: [1800, 400],
      view: { baseUrl: "/v1/orgs/o/videos/v/views", frameSize: [640, 360] },
    });
  });

  it("has nothing to draw with for a moving camera without view files or with a court off the hall image", () => {
    expect(geometryOf({ ...analysis, view_chunks: null }, "/v")).toBeNull(); // an analysis from before
    expect(geometryOf({ ...analysis, calibration: { homography: COURT, image_size: [1280, 720] } }, "/v")).toBeNull();
    expect(geometryOf({ ...analysis, calibration: null }, "/v")).toBeNull();
    expect(geometryOf(null, "/v")).toBeNull();
  });
});

describe("viewAt", () => {
  const file = rows([
    [0, shift(0)],
    [40, shift(4)],
    [80, shift(8)],
    // 80 .. 400: frames the motion pass could not place
    [400, shift(40)],
  ]);

  it("takes the frame's own view and interpolates between neighbouring frames", () => {
    expect(viewAt(file, 40)).toEqual(shift(4));
    expect(viewAt(file, 60)![0]![2]).toBeCloseTo(-6);
  });

  it("draws nothing inside a gap, but a frame close to its edge still counts", () => {
    expect(viewAt(file, 240)).toBeNull();
    expect(viewAt(file, 110)).toEqual(shift(8));
    expect(viewAt(file, 380)).toEqual(shift(40));
    expect(viewAt(file, 520)).toBeNull();
    expect(viewAt(new Float32Array(), 0)).toBeNull();
  });
});

describe("court to picture", () => {
  it("puts a court point where the camera shows it at that moment", () => {
    const at = compose(shift(300), COURT);
    // the centre spot (20, 10) lies at hall px (500, 250); turned by 300 px it is at frame x 200
    expect(project(at, 20, 10, [640, 360])).toEqual([200 / 640, 250 / 360]);
    expect(compose(I, COURT)).toEqual(COURT);
  });

  it("uses the calibration itself for a fixed camera, and the view of the moment for a moving one", () => {
    expect(courtToPicture({ homography: COURT, imageSize: [1280, 720] }, null, 5000)).toEqual({ homography: COURT, size: [1280, 720] });
    const g = geometryOf(analysis, "/v")!;
    const views = { at: (t: number) => (t < 1000 ? shift(300) : t < 2000 ? null : undefined) } as unknown as ViewChunks;
    expect(courtToPicture(g, views, 0)).toEqual({ homography: compose(shift(300), COURT), size: [640, 360] });
    expect(courtToPicture(g, views, 1500)).toBeNull(); // a gap
    expect(courtToPicture(g, views, 2500)).toBeNull(); // still loading
  });
});

describe("ViewChunks", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("fetches each 30 s file once and answers from it", async () => {
    const file = rows([
      [30000, shift(10)],
      [30040, shift(12)],
    ]);
    const fetchMock = vi.fn(async () => new Response(file.buffer as ArrayBuffer));
    vi.stubGlobal("fetch", fetchMock);
    let loaded = 0;
    const views = new ViewChunks("/v/views", 30000, () => loaded++);
    expect(views.at(30020)).toBeUndefined(); // loading
    expect(views.at(30030)).toBeUndefined();
    await vi.waitFor(() => expect(loaded).toBe(1));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/v/views/1", { credentials: "same-origin" });
    expect(views.at(30020)![0]![2]).toBeCloseTo(-11);
  });

  it("draws nothing for a file that is not there", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 404 })));
    let loaded = 0;
    const views = new ViewChunks("/v/views", 30000, () => loaded++);
    views.at(0);
    await vi.waitFor(() => expect(loaded).toBe(1));
    expect(views.at(10)).toBeNull();
  });
});
