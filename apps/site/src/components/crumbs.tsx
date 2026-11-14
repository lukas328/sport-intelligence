import Link from "next/link";

/** Where the page sits, as plain links separated by slashes (no arrows); the last item is the page. */
export function Crumbs({ items, label }: { items: [string, string?][]; label: string }) {
  return (
    <nav aria-label={label}>
      <ol className="flex flex-wrap items-center gap-x-2">
        {items.map(([name, href], i) => (
          <li key={name} className="flex items-center gap-x-2">
            {i > 0 && <span aria-hidden className="text-ink-2">/</span>}
            {href ? (
              <Link href={href} className="link text-ink">
                {name}
              </Link>
            ) : (
              <span aria-current="page">{name}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
