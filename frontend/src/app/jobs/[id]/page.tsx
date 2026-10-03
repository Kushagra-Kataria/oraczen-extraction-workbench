import { JobPage } from '../../../views/JobPage';

export default async function JobRoute({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <JobPage key={id} id={id} />;
}
