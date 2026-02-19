export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 sm:px-6 py-8 sm:py-12">
      <h1 className="mb-6 text-2xl font-bold">Privacy Policy</h1>
      <p className="mb-4 text-muted-foreground">Last updated: February 18, 2026</p>

      <section className="space-y-4 text-sm leading-relaxed">
        <p>
          This application is a private AI assistant tool. It does not collect, sell, or share
          personal data with third parties.
        </p>
        <h2 className="text-lg font-semibold">Data We Process</h2>
        <ul className="list-disc space-y-1 pl-6">
          <li>Messages you send to the assistant via WhatsApp or the web interface</li>
          <li>Your phone number (for WhatsApp message delivery only)</li>
        </ul>
        <h2 className="text-lg font-semibold">Data Retention</h2>
        <p>
          Conversation history is stored locally on our server and is not shared with any external
          services beyond the AI provider used to generate responses.
        </p>
        <h2 className="text-lg font-semibold">Contact</h2>
        <p>For questions, contact the app administrator.</p>
      </section>
    </div>
  );
}
