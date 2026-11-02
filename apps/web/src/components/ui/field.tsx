import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const control =
  "block w-full min-h-10 rounded-md border border-border bg-background px-3 py-2 text-sm " +
  "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent " +
  "aria-[invalid=true]:border-error";

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
      <label htmlFor={inputId} className="block text-sm font-medium">
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
  children,
  id,
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & FieldProps & { children: ReactNode }) {
  const auto = useId();
  const selectId = id ?? auto;
  return (
    <div className="space-y-1">
      <label htmlFor={selectId} className="block text-sm font-medium">
        {label}
      </label>
      <select id={selectId} aria-invalid={error ? true : undefined} className={cn(control, className)} {...props}>
        {children}
      </select>
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
      <input id={boxId} type="checkbox" className="mt-1 size-4 accent-[var(--accent)]" {...props} />
      <label htmlFor={boxId} className="text-sm">
        {label}
      </label>
    </div>
  );
}
