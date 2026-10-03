import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { Layout } from '../components/Layout';
import '../styles.css';

export const metadata: Metadata = {
  title: 'Extraction Workbench',
  description: 'Extract, validate, and review structured customer support records.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Layout>{children}</Layout>
      </body>
    </html>
  );
}
