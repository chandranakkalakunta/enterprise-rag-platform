export default function HomePage() {
  return (
    <main
      style={{
        maxWidth: 720,
        margin: "0 auto",
        padding: "3rem 1.5rem",
        lineHeight: 1.6,
      }}
    >
      <h1 style={{ fontSize: "1.75rem", marginBottom: "0.5rem" }}>
        Enterprise RAG Platform
      </h1>
      <p style={{ color: "#444" }}>
        Phase 0 foundation placeholder. Chat UI, voice, document versioning, and
        analytics land in later phases.
      </p>
      <ul>
        <li>
          API health (local):{" "}
          <code>http://localhost:8000/health</code>
        </li>
        <li>
          Docs: <code>docs/requirements.md</code>
        </li>
        <li>
          Architecture: <code>docs/adr/0001-high-level-architecture.md</code>
        </li>
      </ul>
    </main>
  );
}
