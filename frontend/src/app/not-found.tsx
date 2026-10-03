import Link from 'next/link';

export default function NotFound() {
  return (
    <p>
      Page not found. <Link href="/">Return to the inbox.</Link>
    </p>
  );
}
