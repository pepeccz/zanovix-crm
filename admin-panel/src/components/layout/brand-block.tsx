import Image from "next/image";
import Link from "next/link";

export function BrandBlock() {
  return (
    <Link
      href="/dashboard"
      className="flex items-center gap-2.5 border-b border-zx-rule px-5 py-5"
    >
      <Image
        src="/brand/zanovix-flower.png"
        alt=""
        width={28}
        height={28}
        priority
        className="flex-shrink-0"
      />
      <span className="font-serif text-[18px] leading-none text-zx-ink">
        Zanovix
      </span>
      <span className="ml-auto font-serif text-xs italic text-zx-ink-mute">
        CRM
      </span>
    </Link>
  );
}
