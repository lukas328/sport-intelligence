"use client";

import { CalendarDays } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useRef } from "react";
import { control } from "@/components/ui/field";
import { formatDate, isoDay, parseDate, parseTime } from "@/lib/date-input";
import { cn } from "@/lib/utils";

/**
 * Date and kick-off time written the Swiss way (L16): «16.11.2026» and «20:15», never the format of
 * the browser's language. The calendar button opens the phone's own date picker; what it picks is
 * written back in our format. `time` null: only the day (a scouting video).
 */
export function DateTimeField({
  date,
  time,
  onDate,
  onTime,
  dateLabel,
  timeLabel,
  required = false,
}: {
  date: string;
  time?: string | null;
  onDate: (v: string) => void;
  onTime?: (v: string) => void;
  dateLabel: string;
  timeLabel?: string;
  required?: boolean;
}) {
  const t = useTranslations("dateField");
  const id = useId();
  const picker = useRef<HTMLInputElement>(null);
  const badDate = date.trim() !== "" && parseDate(date) == null;
  const badTime = time != null && time.trim() !== "" && parseTime(time) == null;
  return (
    <div className={cn("grid gap-3", time != null && "grid-cols-[minmax(0,1fr)_7.5rem]")}>
      <div className="space-y-1">
        <label htmlFor={`${id}-d`} className="block text-sm font-semibold">
          {dateLabel}
        </label>
        <div className="relative">
          <input
            id={`${id}-d`}
            name="date"
            inputMode="numeric"
            autoComplete="off"
            placeholder={t("datePlaceholder")}
            value={date}
            required={required}
            onChange={(e) => onDate(e.target.value)}
            aria-invalid={badDate || undefined}
            aria-describedby={`${id}-dh`}
            className={cn(control, "pr-11")}
            data-testid="date-input"
          />
          <button
            type="button"
            className="absolute inset-y-0 right-0 grid w-11 cursor-pointer place-items-center border-0 bg-transparent text-ink"
            aria-label={t("pick")}
            onClick={() => {
              const el = picker.current;
              if (!el) return;
              el.value = isoDay(date);
              try {
                el.showPicker();
              } catch {
                el.click();
              }
            }}
          >
            <CalendarDays aria-hidden className="size-5" />
          </button>
          {/* the device's picker; its value comes back in our format */}
          <input
            ref={picker}
            type="date"
            tabIndex={-1}
            aria-hidden
            className="pointer-events-none absolute right-0 bottom-0 size-px opacity-0"
            onChange={(e) => {
              const [y, m, d] = e.target.value.split("-").map(Number);
              if (y && m && d) onDate(formatDate(new Date(y, m - 1, d)));
            }}
          />
        </div>
        <p id={`${id}-dh`} className={cn("text-xs", badDate ? "text-error" : "text-muted")}>
          {badDate ? t("dateInvalid") : t("dateHint")}
        </p>
      </div>
      {time != null && onTime && (
        <div className="space-y-1">
          <label htmlFor={`${id}-t`} className="block text-sm font-semibold">
            {timeLabel}
          </label>
          <input
            id={`${id}-t`}
            name="time"
            inputMode="numeric"
            autoComplete="off"
            placeholder={t("timePlaceholder")}
            value={time}
            required={required}
            onChange={(e) => onTime(e.target.value)}
            onBlur={() => {
              const p = parseTime(time);
              if (p) onTime(`${String(p[0]).padStart(2, "0")}:${String(p[1]).padStart(2, "0")}`);
            }}
            aria-invalid={badTime || undefined}
            aria-describedby={`${id}-th`}
            className={control}
            data-testid="time-input"
          />
          <p id={`${id}-th`} className={cn("text-xs", badTime ? "text-error" : "text-muted")}>
            {badTime ? t("timeInvalid") : t("timeHint")}
          </p>
        </div>
      )}
    </div>
  );
}
