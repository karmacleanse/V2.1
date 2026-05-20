import { Link } from 'react-router-dom';

const Section = ({ number, title, children }) => (
  <section className="mb-10" data-testid={`terms-section-${number}`}>
    <div
      className="text-xs uppercase font-bold tracking-widest mb-2"
      style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
    >
      §{number}
    </div>
    <h2
      className="text-xl sm:text-2xl font-black uppercase tracking-tight mb-4"
      style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
    >
      {title}
    </h2>
    <div
      className="text-sm leading-relaxed space-y-3"
      style={{ color: '#0A0A0A', fontFamily: 'IBM Plex Mono, monospace' }}
    >
      {children}
    </div>
  </section>
);

const List = ({ items }) => (
  <ul className="pl-6 space-y-1" style={{ listStyleType: 'square' }}>
    {items.map((it, i) => (
      <li key={i}>{it}</li>
    ))}
  </ul>
);

const Doc = ({ title, revision, children }) => (
  <div
    className="border-2 p-6 sm:p-10 mb-8"
    style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}
  >
    <div className="mb-8 pb-6" style={{ borderBottom: '2px solid #0A0A0A' }}>
      <h1
        className="text-3xl sm:text-4xl font-black uppercase tracking-tight"
        style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
      >
        {title}
      </h1>
      <div
        className="text-xs uppercase tracking-widest mt-2"
        style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
      >
        {revision}
      </div>
    </div>
    {children}
  </div>
);

const Terms = () => {
  return (
    <div
      className="min-h-screen px-4 py-10"
      style={{ background: '#F4F4F0' }}
      data-testid="terms-page"
    >
      <div className="max-w-3xl mx-auto">
        {/* Top nav */}
        <div className="mb-8 flex items-center justify-between">
          <Link
            to="/"
            className="text-xs uppercase font-bold tracking-widest hover:underline"
            style={{ color: '#0A0A0A', fontFamily: 'IBM Plex Mono, monospace' }}
            data-testid="terms-back-link"
          >
            ← Karma Cleanse
          </Link>
          <div
            className="text-xs uppercase tracking-widest"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Document Bundle 2026.05
          </div>
        </div>

        {/* Welcome */}
        <Doc title="Operational Terms" revision="Last updated: May 2026">
          <p
            className="text-sm mb-6 leading-relaxed"
            style={{ color: '#0A0A0A', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Welcome to Karma Cleanse.
            <br />
            By accessing or using this platform, you acknowledge that you have read,
            understood, and voluntarily agreed to these Operational Terms.
          </p>

          <Section number="1" title="Nature of the Platform">
            <p>Karma Cleanse is a satirical digital entertainment project presented in the form of an absurdist symbolic ritual interface.</p>
            <p>The platform is intended for:</p>
            <List items={[
              'humor',
              'artistic expression',
              'parody',
              'symbolic participation',
              'fictional bureaucratic roleplay',
              'self-reflective entertainment',
            ]} />
            <p className="mt-3">Karma Cleanse does not provide:</p>
            <List items={[
              'religious services',
              'spiritual services',
              'therapy',
              'psychological treatment',
              'legal certification',
              'financial advice',
              'scientific evaluation',
              'metaphysical intervention',
            ]} />
            <p className="mt-3">All generated certificates, diagnostics, statuses, warnings, protocols, classifications, karmic assessments, institutional references, and procedural outputs are entirely fictional.</p>
          </Section>

          <Section number="2" title="Symbolic Participation">
            <p>The platform functions solely as a symbolic visualization framework.</p>
            <p>Karma Cleanse does not alter karma, morality, destiny, interpersonal outcomes, emotional conditions, metaphysical states, universal balance, or reality itself.</p>
            <p>Any perceived sense of relief, absolution, resolution, emotional release, closure, "cleansing", or balance exists exclusively within the subjective interpretation of the participant.</p>
            <p>The service merely visualizes and dramatizes symbolic participation through fictional interfaces, generated procedures, certificates, and ceremonial interactions.</p>
          </Section>

          <Section number="3" title="Voluntary Contributions">
            <p>Any payment, contribution, donation, compensation, transfer, or digital support submitted through the platform is entirely voluntary.</p>
            <p>Contributions are provided:</p>
            <List items={[
              'as symbolic participation',
              'as support for the project',
              'as appreciation of the experience',
              'as participation in the joke',
            ]} />
            <p className="mt-3">Contributions do not constitute:</p>
            <List items={[
              'the purchase of a guaranteed outcome',
              'the acquisition of spiritual services',
              'the purchase of moral absolution',
              'the purchase of emotional improvement',
              'the purchase of supernatural intervention',
            ]} />
            <p className="mt-3">The operator makes no representation regarding future allocation, preservation, charitable or operational use, storage, conversion, or expenditure priorities of funds.</p>
            <p>Contributed amounts may be retained, spent, redistributed, ignored, archived, converted into consumable goods, used operationally or non-operationally, or otherwise utilized at the sole discretion of the operator.</p>
          </Section>

          <Section number="4" title="Certificates & Generated Content">
            <p>All certificates generated by Karma Cleanse are fictional symbolic artifacts.</p>
            <p>Certificates have no legal authority, no governmental recognition, no religious validity, no psychological authority, and no institutional standing.</p>
            <p>Verification systems exist solely as part of the fictional experience.</p>
            <p>Any resemblance to official infrastructure, institutional language, compliance systems, or bureaucratic processes is intentional and comedic.</p>
          </Section>

          <Section number="5" title="User Responsibility">
            <p>Users participate voluntarily and at their own discretion.</p>
            <p>You agree not to interpret the platform as medical advice, therapy, legal guidance, spiritual instruction, financial consultation, or factual evaluation of morality or character.</p>
            <p>You remain solely responsible for your decisions, actions, relationships, interpretations, beliefs, and emotional responses.</p>
          </Section>

          <Section number="6" title="Refund Policy">
            <p>Due to the symbolic and voluntary nature of contributions, refunds are generally not provided.</p>
            <p>The operator retains full discretion regarding refund eligibility, reversals, contribution disputes, and symbolic compensation outcomes.</p>
          </Section>

          <Section number="7" title="Limitation of Liability">
            <p>To the maximum extent permitted by applicable law, Karma Cleanse and its operators shall not be liable for:</p>
            <List items={[
              'emotional decisions',
              'interpersonal consequences',
              'misunderstandings',
              'existential crises',
              'impulsive apologies',
              'relationship outcomes',
              'cosmic disappointment',
              'timeline instability',
              'perceived karmic fluctuations',
            ]} />
            <p className="mt-3">Participation occurs entirely at the user's own discretion and risk.</p>
          </Section>

          <Section number="8" title="Age Requirement">
            <p>You must be at least 18 years old, or the age of digital consent in your jurisdiction, to use this platform.</p>
          </Section>

          <Section number="9" title="Modifications">
            <p>The platform, its procedures, fictional protocols, pricing structures, symbolic classifications, and generated ceremonial systems may be modified, suspended, replaced, destabilized, or discontinued at any time without notice.</p>
          </Section>

          <Section number="10" title="Final Statement">
            <p>Karma Cleanse is an intentionally overengineered emotional bureaucracy simulator.</p>
            <p>Nothing more should be inferred.</p>
          </Section>
        </Doc>

        {/* Jurisdictional Disclaimer */}
        <Doc title="Jurisdictional Disclaimer" revision="Revision 2.3">
          <div
            className="text-sm leading-relaxed space-y-3"
            style={{ color: '#0A0A0A', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            <p>Karma Cleanse is a fictional absurdist internet project.</p>
            <p>The platform should not be interpreted as religion, therapy, spiritual guidance, scientific analysis, emotional counseling, metaphysical intervention, legal certification, or institutional authority.</p>
            <p>All karmic diagnostics, emotional statuses, bureaucratic classifications, absolution procedures, cosmic references, timeline disturbances, and verification protocols are fictional and generated for entertainment purposes only.</p>
            <p>The platform performs no supernatural, therapeutic, scientific, or religious function.</p>
            <p>Any emotional meaning perceived by the participant originates entirely from the participant's own interpretation.</p>
            <p>Any resemblance to official systems, institutional structures, or administrative authority is deliberate satire.</p>
          </div>
        </Doc>

        {/* Privacy Policy */}
        <Doc title="Privacy Policy" revision="Last updated: May 2026">
          <div
            className="text-sm leading-relaxed space-y-3"
            style={{ color: '#0A0A0A', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            <p>Karma Cleanse may collect limited technical and operational information required for platform functionality.</p>
            <p>This may include:</p>
            <List items={[
              'browser information',
              'IP address',
              'device data',
              'anonymous analytics',
              'generated certificate identifiers',
              'voluntary email submissions',
              'payment metadata',
              'interaction events',
            ]} />
            <p className="mt-3">The platform may use cookies, analytics tools, payment processors, hosting infrastructure, and third-party technical providers.</p>
            <p>Karma Cleanse does not guarantee permanent storage of certificates, generated content, symbolic records, ritual history, or emotional classifications.</p>
            <p>Some generated materials may be removed, archived, destabilized, or disappear unexpectedly.</p>
            <p>By using the platform, you acknowledge that internet systems are inherently imperfect, emotionally unstable, and occasionally absurd.</p>
          </div>
        </Doc>

        {/* Contribution Policy */}
        <Doc title="Contribution Policy" revision="Last updated: May 2026">
          <div
            className="text-sm leading-relaxed space-y-3"
            style={{ color: '#0A0A0A', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            <p>All contributions made through Karma Cleanse are voluntary, symbolic, non-contractual, and entertainment-oriented.</p>
            <p>Contributions are intended as optional support for the continued existence of the project and its associated absurdities.</p>
            <p>No contribution guarantees:</p>
            <List items={[
              'karmic improvement',
              'emotional recovery',
              'forgiveness',
              'luck',
              'redemption',
              'metaphysical balance',
              'interpersonal success',
              'spiritual advancement',
            ]} />
            <p className="mt-3">The operator reserves complete discretion regarding fund allocation, operational spending, infrastructure costs, artistic development, snack acquisition, and future use of contributed funds.</p>
            <p>Participation implies acknowledgment of the symbolic and fictional nature of the platform.</p>
          </div>
        </Doc>

        {/* Footer back-link */}
        <div className="text-center pt-4 pb-8">
          <Link
            to="/"
            className="inline-block px-6 py-3 font-bold uppercase text-sm border-2 transition-colors"
            style={{
              background: '#0A0A0A',
              color: '#F4F4F0',
              borderColor: '#0A0A0A',
              fontFamily: 'Chivo, sans-serif',
            }}
            data-testid="terms-return-btn"
          >
            Return to Karma Cleanse
          </Link>
          <p
            className="text-xs mt-6"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Emotional bureaucracy since 2026.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Terms;
