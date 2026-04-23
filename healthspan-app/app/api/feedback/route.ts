import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";
import { DailyEntry, FeedbackEntry } from "@/lib/types";
import { generateId, entryAvgs, avg } from "@/lib/utils";
import { wellnessScore } from "@/lib/storage";

const client = new Anthropic();

function buildPrompt(
  entries: DailyEntry[],
  recentEntries: DailyEntry[],
  olderEntries: DailyEntry[],
  goals: { category: string; label: string; targetValue: number; unit: string }[]
): string {
  const recentAvg = entryAvgs(recentEntries);
  const olderAvg = entryAvgs(olderEntries);
  const latestEntry = recentEntries[0];
  const totalDays = entries.length;

  const recentScores = recentEntries.map(wellnessScore);
  const olderScores = olderEntries.map(wellnessScore);
  const recentAvgScore = avg(recentScores);
  const olderAvgScore = avg(olderScores);

  let prompt = `You are a personalized healthspan coach. Analyze this person's health data and provide meaningful, specific, and encouraging feedback that evolves with their journey.

CONTEXT:
- Total days tracked: ${totalDays}
- Recent wellness score (7-day avg): ${recentAvgScore.toFixed(0)}/100
- Previous wellness score (prior week avg): ${olderAvgScore.toFixed(0)}/100
`;

  if (latestEntry) {
    prompt += `
TODAY'S DATA:
- Sleep: ${latestEntry.sleep.hours}h, quality ${latestEntry.sleep.quality}/10
- Exercise: ${latestEntry.exercise.minutes} min at intensity ${latestEntry.exercise.intensity}/5
- Nutrition: quality ${latestEntry.nutrition.quality}/10, ${latestEntry.nutrition.meals} meals, ${latestEntry.nutrition.water} glasses water
- Stress: ${latestEntry.stress}/10 (lower is better)
- Mood: ${latestEntry.mood}/10
- Energy: ${latestEntry.energy}/10
- Social connection: ${latestEntry.social}/5
${latestEntry.notes ? `- Notes: "${latestEntry.notes}"` : ""}
`;
  }

  if (recentAvg && olderAvg) {
    prompt += `
RECENT 7-DAY AVERAGES vs PRIOR WEEK:
- Sleep: ${recentAvg.sleepHours.toFixed(1)}h (was ${olderAvg.sleepHours.toFixed(1)}h)
- Exercise: ${recentAvg.exerciseMinutes.toFixed(0)}min (was ${olderAvg.exerciseMinutes.toFixed(0)}min)
- Nutrition quality: ${recentAvg.nutritionQuality.toFixed(1)} (was ${olderAvg.nutritionQuality.toFixed(1)})
- Stress: ${recentAvg.stress.toFixed(1)} (was ${olderAvg.stress.toFixed(1)})
- Mood: ${recentAvg.mood.toFixed(1)} (was ${olderAvg.mood.toFixed(1)})
- Energy: ${recentAvg.energy.toFixed(1)} (was ${olderAvg.energy.toFixed(1)})
`;
  } else if (recentAvg) {
    prompt += `
RECENT 7-DAY AVERAGES:
- Sleep: ${recentAvg.sleepHours.toFixed(1)}h, quality ${recentAvg.sleepQuality.toFixed(1)}/10
- Exercise: ${recentAvg.exerciseMinutes.toFixed(0)}min/day
- Nutrition quality: ${recentAvg.nutritionQuality.toFixed(1)}/10, water ${recentAvg.water.toFixed(1)} glasses
- Stress: ${recentAvg.stress.toFixed(1)}/10
- Mood: ${recentAvg.mood.toFixed(1)}/10, Energy: ${recentAvg.energy.toFixed(1)}/10
`;
  }

  if (goals.length > 0) {
    prompt += `
ACTIVE GOALS:
${goals.map((g) => `- ${g.label}: target ${g.targetValue} ${g.unit}`).join("\n")}
`;
  }

  // Tone adjusts based on journey stage
  if (totalDays <= 3) {
    prompt += "\nThis person is just starting their healthspan journey. Be warm, encouraging, and focus on building momentum rather than optimization.";
  } else if (totalDays <= 14) {
    prompt += "\nThis person is building new habits. Acknowledge their consistency and help them identify early patterns.";
  } else if (totalDays <= 30) {
    prompt += "\nThis person is developing a solid routine. Provide more specific insights and help them refine their approach.";
  } else {
    prompt += "\nThis person is a committed healthspan practitioner. Provide nuanced, data-driven insights and help them optimize their longevity practices.";
  }

  prompt += `

Respond with a JSON object with these exact fields:
{
  "feedback": "A 2-3 sentence personalized message that feels warm, specific, and insightful. Reference their actual data. Show that you understand their journey.",
  "highlights": ["Up to 2 specific things they're doing well, be specific with numbers"],
  "actionItems": ["1-2 concrete, specific actions they can take tomorrow or this week"],
  "overallScore": <number 0-100 representing their current wellness>,
  "trend": "<improving|stable|declining>"
}

Be conversational, not clinical. Focus on what matters most for long-term healthspan.`;

  return prompt;
}

export async function POST(req: NextRequest) {
  try {
    const { entries, goals } = await req.json() as {
      entries: DailyEntry[];
      goals: { category: string; label: string; targetValue: number; unit: string }[];
    };

    if (!entries || entries.length === 0) {
      return NextResponse.json(
        { error: "No entries provided" },
        { status: 400 }
      );
    }

    const sorted = [...entries].sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );
    const recentEntries = sorted.slice(0, 7);
    const olderEntries = sorted.slice(7, 14);

    const prompt = buildPrompt(sorted, recentEntries, olderEntries, goals);

    const message = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 600,
      system: "You are a compassionate, science-based healthspan coach. Always respond with valid JSON only, no markdown.",
      messages: [{ role: "user", content: prompt }],
    });

    const text = message.content[0].type === "text" ? message.content[0].text : "";
    const parsed = JSON.parse(text);

    const feedbackEntry: FeedbackEntry = {
      id: generateId(),
      date: new Date().toISOString(),
      feedback: parsed.feedback || "",
      highlights: parsed.highlights || [],
      actionItems: parsed.actionItems || [],
      overallScore: parsed.overallScore || 0,
      trend: parsed.trend || "stable",
    };

    return NextResponse.json(feedbackEntry);
  } catch (err) {
    console.error("Feedback API error:", err);
    return NextResponse.json(
      { error: "Failed to generate feedback" },
      { status: 500 }
    );
  }
}
