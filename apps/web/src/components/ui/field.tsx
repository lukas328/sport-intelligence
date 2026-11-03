import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const control =
  "block w-full min-h-10 rounded-xl border-0 bg-raised px-3 py-2 text-sm text-foreground ring-1 ring-inset ring-border " +
  "placeholder:text-muted/70 transition-shadow hover:ring-muted/40 " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent " +
  "aria-[invalid=true]:ring-error disabled:opacity-60";

interface FieldProps {
  label: string;
  error?: string | undefined;
  hint?: string | undefined;
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & FieldProps>(function Input(
  { label, error, hint, className, id, ...props },
  ref,
) {
  const auto = useId();
  const inputId = id ?? auto;
  return (
    <div className="space-y-1">
      <label htmlFor={inputId} className="block text-[0.8125rem] font-medium">
        {label}
      </label>
      <input
        ref={ref}
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
        className={cn(control, className)}
        {...props}
      />
      {hint && !error && (
        <p id={`${inputId}-hint`} className="text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${inputId}-error`} className="text-xs text-error">
          {error}
        </p>
      )}
    </div>
  );
});

export function Select({
  label,
  error,
  hint,
  children,
  id,
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & FieldProps & { children: ReactNode }) {
  const auto = useId();
  const selectId = id ?? auto;
  return (
    <div className="space-y-1">
      <label htmlFor={selectId} className="block text-[0.8125rem] font-medium">
        {label}
      </label>
      <select
        id={selectId}
        aria-invalid={error ? true : undefined}
        aria-describedby={hint && !error ? `${selectId}-hint` : undefined}
        className={cn(control, className)}
        {...props}
      >
        {children}
      </select>
      {hint && !error && (
        <p id={`${selectId}-hint`} className="text-xs text-muted">
          {hint}
        </p>
      )}
      {error && <p className="text-xs text-error">{error}</p>}
    </div>
  );
}

export function Checkbox({
  label,
  id,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: ReactNode }) {
  const auto = useId();
  const boxId = id ?? auto;
  return (
    <div className="flex items-start gap-2">
      <input id={boxId} type="checkbox" className="mt-0.5 size-4 rounded accent-[var(--accent)]" {...props} />
      <label htmlFor={boxId} className="text-sm">
        {label}
      </label>
    </div>
  );
}
