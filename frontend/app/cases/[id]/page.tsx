// Screen 2: Case Detail — the single most important screen for the demo.
export default function CaseDetailPage({ params }: { params: { id: string } }) {
  return <main>Case {params.id} — full reasoning timeline.</main>;
}
