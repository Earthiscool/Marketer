export type MarketingAgentInput = {
  objective: string;
  market: string;
  offer: string;
  location: string;
  audience: string;
  constraints: string;
};

export type MarketingAgentOutput = {
  positioning: {
    headline: string;
    angle: string;
    proof: string[];
  };
  customerTargets: Array<{
    segment: string;
    pain: string;
    trigger: string;
    whereToFind: string[];
    pitch: string;
  }>;
  campaignPlan: Array<{
    channel: string;
    action: string;
    cadence: string;
    successMetric: string;
  }>;
  outreach: {
    coldEmail: string;
    dm: string;
    callScript: string;
    followUp: string;
  };
  content: {
    googleBusinessPosts: string[];
    linkedinPosts: string[];
    blogIdeas: string[];
    landingPageSections: string[];
  };
  weeklyExecution: Array<{
    day: string;
    priority: string;
    tasks: string[];
  }>;
  leadScoring: Array<{
    signal: string;
    score: number;
    reason: string;
  }>;
  cautions: string[];
};

export type ProspectInput = {
  businessName: string;
  website?: string;
  email?: string;
  phone?: string;
  location?: string;
  notes?: string;
};

export type ProspectAnalysis = ProspectInput & {
  score: number;
  status: "new" | "approved" | "contacted" | "follow_up" | "not_fit";
  fit: "high" | "medium" | "low";
  specificObservation: string;
  opportunity: string;
  recommendedOffer: string;
  subject: string;
  emailDraft: string;
  dmDraft: string;
  followUpDraft: string;
  nextAction: string;
  researchNotes: string[];
};

export const summitMarketingContext = `
Summit Intelligent Systems builds custom AI-powered websites, chatbots, booking systems, local SEO systems, analytics, and automation for local businesses.
Core offer: no service cost. Clients pay only their own domain and hosting. Clients own 100% of the code and assets.
Positioning: student engineers building real portfolio proof through successful local business projects.
Typical launch: 7 to 10 business days after application and strategy call.
Primary CTA: apply for a free partner spot at summitintelligentsystems.com/apply.
Availability claim currently used on the site: accepting Q2 2026 partners, 3 spots remaining.
Best-fit customers: local businesses that need more calls, appointments, orders, quote requests, or Google search visibility.
Proof points: Lohani Paints grew from 500 to 15,000 monthly clicks after a rebuild, AI catalog, SEO overhaul, and Google Business integration. Blue Skies Pottery launched e-commerce and increased audience reach by 180%.
Tone: direct, helpful, confident, no hype, no jargon, no fake guarantees.
`;

export function buildFallbackMarketingPlan(input: MarketingAgentInput): MarketingAgentOutput {
  const market = input.market || "local businesses";
  const location = input.location || "your target area";
  const offer = input.offer || "free AI-powered websites, automation, and local SEO";

  return {
    positioning: {
      headline: `Free AI websites for ${market} in ${location}`,
      angle: `Lead with the sharpest differentiator: Summit offers ${offer} and backs it with real local-business proof.`,
      proof: [
        "Clients own the code and assets after launch.",
        "Typical launch window is 7 to 10 business days.",
        "Lohani Paints grew from 500 to 15,000 monthly search clicks after the rebuild.",
        "Blue Skies Pottery increased audience reach by 180% after launch.",
      ],
    },
    customerTargets: [
      {
        segment: "Service businesses with slow websites",
        pain: "They lose quote requests because customers cannot quickly understand services, pricing, or availability.",
        trigger: "Their Google profile has recent reviews but their website feels outdated or incomplete.",
        whereToFind: ["Google Maps", "local chamber directories", "Facebook community groups"],
        pitch: "Rebuild the site, add an AI intake assistant, and make every service page easier to find on Google at no service cost.",
      },
      {
        segment: "Appointment-based local businesses",
        pain: "They spend too much time answering repeat questions and manually scheduling leads.",
        trigger: "They mention booking, calls, or DMs as the main way customers contact them.",
        whereToFind: ["Instagram", "Google Business Profile", "Yelp"],
        pitch: "Add a 24/7 AI assistant that answers common questions and routes serious customers toward booking.",
      },
      {
        segment: "Retail shops with local search potential",
        pain: "They have real products and loyal customers but weak online discovery.",
        trigger: "They post products socially but do not have strong searchable product or collection pages.",
        whereToFind: ["Instagram", "Main Street business lists", "local market vendor pages"],
        pitch: "Turn the business into a fast searchable site with product pages, local SEO, and a customer-facing AI guide.",
      },
    ],
    campaignPlan: [
      {
        channel: "Google Maps prospecting",
        action: "Find businesses with good reviews, outdated sites, no booking flow, or missing service pages. Send a short audit with one specific missed opportunity.",
        cadence: "25 prospects per weekday",
        successMetric: "5 percent reply rate and 2 booked strategy calls per week",
      },
      {
        channel: "Founder-led cold email",
        action: "Send personalized emails from Agastya using one visible problem from the business website or Google profile.",
        cadence: "50 highly targeted emails per week",
        successMetric: "8 replies and 3 applications per week",
      },
      {
        channel: "LinkedIn and local groups",
        action: "Post weekly public teardowns of common local business website mistakes, then offer free help to qualified businesses.",
        cadence: "3 posts and 10 comments per week",
        successMetric: "10 profile conversations per week",
      },
    ],
    outreach: {
      coldEmail: `Subject: Quick idea for {{business_name}}\n\nHi {{first_name}},\n\nI noticed {{specific_observation}}.\n\nI run Summit Intelligent Systems. We build custom AI websites, booking assistants, and local SEO systems for local businesses at no service cost. You only cover your own domain and hosting, and you own the finished site.\n\nOpen to a 15 minute strategy call this week?`,
      dm: `Saw {{business_name}} and had a practical idea: {{specific_improvement}}. Summit builds custom AI websites and lead intake systems for local businesses at no service cost. Want me to send the quick audit?`,
      callScript: `Hi, this is Agastya from Summit Intelligent Systems. We help local businesses get better websites, AI intake, and local SEO without charging a service fee. I noticed {{specific_observation}} and thought there may be an easy win around {{specific_improvement}}.`,
      followUp: `Quick follow-up in case this got buried. {{business_name}} looks like the kind of local business where a custom site plus AI intake could create a visible lift. Should I send over the specific audit notes?`,
    },
    content: {
      googleBusinessPosts: [
        "Local businesses should not have to spend $10,000 to get a fast website, AI assistant, and local SEO.",
        "If your website does not answer customer questions instantly, your competitors are probably getting the lead.",
      ],
      linkedinPosts: [
        "A local business website has one job: turn trust into action.",
        "Most small businesses do not need a bigger marketing budget first. They need a faster site, clearer offer, stronger Google presence, and fewer manual steps.",
      ],
      blogIdeas: [
        "The 12-point website audit every local business should run before buying ads",
        "How AI chatbots help local businesses capture leads after hours",
      ],
      landingPageSections: [
        "Hero: Free AI websites for local businesses that need more calls, bookings, and customers.",
        "Proof: show local business outcomes with clear before and after metrics.",
      ],
    },
    weeklyExecution: [
      { day: "Monday", priority: "Prospect list", tasks: ["Build 100 Google Maps leads", "Score each lead", "Write 20 personalized openers"] },
      { day: "Tuesday", priority: "Outbound", tasks: ["Send 25 emails", "Send 10 social DMs", "Log replies and objections"] },
      { day: "Wednesday", priority: "Proof content", tasks: ["Publish one case-study post", "Create one short audit example"] },
      { day: "Thursday", priority: "Follow-up", tasks: ["Follow up with all non-replies", "Offer 15 minute strategy calls"] },
      { day: "Friday", priority: "Improve conversion", tasks: ["Review replies", "Update scripts", "Add one objection answer"] },
    ],
    leadScoring: [
      { signal: "No website or broken website", score: 25, reason: "High urgency and clear value proposition." },
      { signal: "Good reviews but weak SEO pages", score: 20, reason: "They already have trust but are missing discovery." },
      { signal: "Manual booking or inquiry process", score: 15, reason: "AI intake and booking automation can save time quickly." },
    ],
    cautions: [
      "Do not promise guaranteed rankings or revenue.",
      "Do not over-message businesses that decline.",
      "Keep the free offer clear: service fee is $0, but domain and hosting are still paid by the client.",
    ],
  };
}

export function parseProspects(raw: string): ProspectInput[] {
  return raw
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 25)
    .map((line) => {
      const parts = line.split(",").map((part) => part.trim()).filter(Boolean);
      const website = parts.find((part) => /^https?:\/\//i.test(part) || /\.[a-z]{2,}/i.test(part));
      const email = parts.find((part) => /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/.test(part));
      const phone = parts.find((part) => /(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/.test(part));
      const businessName = parts[0] || line;
      const notes = parts.filter((part) => part !== businessName && part !== website && part !== email && part !== phone).join(", ");

      return {
        businessName,
        website: website ? normalizeWebsite(website) : undefined,
        email,
        phone,
        notes: notes || undefined,
      };
    });
}

export function normalizeWebsite(value: string): string {
  if (!value) return value;
  if (/^https?:\/\//i.test(value)) return value;
  return `https://${value}`;
}

export function buildFallbackProspectAnalysis(prospect: ProspectInput): ProspectAnalysis {
  const hasWebsite = Boolean(prospect.website);
  const notes = prospect.notes || "";
  const weakSiteSignal = !hasWebsite || /outdated|slow|no booking|no seo|bad|old|facebook only|instagram only/i.test(notes);
  const score = weakSiteSignal ? 78 : 58;
  const opportunity = weakSiteSignal
    ? "There may be a fast win around a clearer website, AI lead intake, and local SEO pages."
    : "There may be an opportunity to improve conversion with AI intake, stronger proof, and clearer calls to action.";

  return {
    ...prospect,
    score,
    status: "new",
    fit: score >= 75 ? "high" : score >= 55 ? "medium" : "low",
    specificObservation: hasWebsite
      ? `I reviewed ${prospect.website} and would check whether the site clearly turns visitors into calls, bookings, or quote requests.`
      : `${prospect.businessName} does not have a website listed in this lead record, which is usually a strong opening for Summit.`,
    opportunity,
    recommendedOffer: "Free AI-powered website rebuild with lead intake, local SEO, analytics, and full code ownership.",
    subject: `Quick website idea for ${prospect.businessName}`,
    emailDraft: `Hi {{first_name}},\n\nI came across ${prospect.businessName} and noticed one practical opportunity: ${opportunity}\n\nI run Summit Intelligent Systems. We build custom AI websites, booking assistants, and local SEO systems for local businesses at no service cost. You only cover your own domain and hosting, and you own the finished site.\n\nOpen to a 15-minute strategy call this week?`,
    dmDraft: `Saw ${prospect.businessName} and had a practical idea: ${opportunity} Summit builds custom AI websites and lead intake systems for local businesses at no service cost. Want me to send the quick audit?`,
    followUpDraft: `Quick follow-up in case this got buried. ${prospect.businessName} looks like a business where a custom site plus AI intake could create a visible operational win. Should I send over the specific audit notes?`,
    nextAction: prospect.email ? "Review and approve the email draft, then send it manually or through a connected email provider." : "Find the owner's email or contact form, then approve outreach.",
    researchNotes: [
      "Use a real business-specific detail before sending.",
      "Do not promise guaranteed rankings, revenue, or customer volume.",
    ],
  };
}
