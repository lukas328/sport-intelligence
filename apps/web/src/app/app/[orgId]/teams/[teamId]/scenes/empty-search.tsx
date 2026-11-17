"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { linkClass } from "@/components/anlauf/blocks";

/**
 * The scene search before the first video (finding A6): the field takes a question and answers it
 * on Enter, instead of staying silent. The answer says why nothing is found and the way out of it
 * (the upload, for those who may upload).
 */
export function EmptySceneSearch({ uploadHref, focus }: { uploadHref: string | null; focus: boolean }) {
  const t = useTranslations("scenesPage");
  const ta = useTranslations("anlauf");
  const [asked, setAsked] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  // «Suchen» elsewhere leads here with ?focus=1: the cursor stands in the field
  useEffect(() => {
    if (focus) input.current?.focus();
  }, [focus]);
  return (
    <form
      role="search"
      className="mb-10 max-w-3xl"
      onSubmit={(e) => {
        e.preventDefault();
        setAsked(true);
      }}
    >
      <label className="flex min-h-16 items-center gap-3 border-2 border-ink bg-paper px-[18px] text-xl font-semibold focus-within:outline-3 focus-within:outline-offset-2 focus-within:outline-ink">
        <Search aria-hidden className="size-[22px] shrink-0" strokeWidth={2.2} />
        <span className="sr-only">{t("searchLabel")}</span>
        <input
          ref={input}
          type="search"
          enterKeyHint="search"
          aria-describedby="scenes-empty-search"
          placeholder={t("placeholder")}
          onChange={() => setAsked(false)}
          className="min-w-0 flex-1 bg-transparent font-semibold text-ink outline-none placeholder:text-ink-2 [&::-webkit-search-cancel-button]:appearance-none"
          data-testid="scene-search"
        />
      </label>
      {/* the answer is read out when it appears; before a question the field says from when it finds something */}
      <div id="scenes-empty-search" role="status" className="mt-3 text-[15px]">
        {asked ? (
          <p className="m-0 border-l-4 border-ink bg-paper px-4 py-3 text-[17px] font-semibold" data-testid="scenes-empty-answer">
            {uploadHref ? t("emptyAnswer") : t("emptyAnswerRead")}
            {uploadHref && (
              <>
                {" "}
                <Link href={uploadHref} className={linkClass}>
                  {ta("uploadVideo")}
                </Link>
              </>
            )}
          </p>
        ) : (
          <p className="m-0 font-semibold text-ink-2">{t("emptySearch")}</p>
        )}
      </div>
    </form>
  );
}
