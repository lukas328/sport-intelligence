/** What a camera or a phone writes; anything else is not sent at all (UX test B29). */
const VIDEO_EXT = /\.(mp4|m4v|mov|mkv|avi|webm|mts|m2ts|3gp|mpg|mpeg)$/i;

export const looksLikeVideo = (f: { name: string; type: string }): boolean => f.type.startsWith("video/") || VIDEO_EXT.test(f.name);
