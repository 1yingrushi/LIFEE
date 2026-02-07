export interface Env {
	GEMINI_API_KEY: string;
  }
  
  const corsHeaders: Record<string, string> = {
	"Access-Control-Allow-Origin": "*",
	"Access-Control-Allow-Methods": "POST, OPTIONS",
	"Access-Control-Allow-Headers": "Content-Type",
  };
  
  type Persona = {
	id: string;
	name: string;
	prompt?: string; // persona-specific style/behavior instruction (optional)
  };
  
  type Body = {
	situation?: string;
	question?: string;
	userInput?: string; // 前端每一轮用户输入（可选）
	personas?: Persona[];
	birthDate?: string; // YYYY-MM-DD (Gregorian)
  };
  
  function extractJsonObject(text: string): any | null {
	// 尝试从模型输出中“抠出”第一个完整 JSON 对象
	const first = text.indexOf("{");
	const last = text.lastIndexOf("}");
	if (first === -1 || last === -1 || last <= first) return null;
  
	const maybe = text.slice(first, last + 1).trim();
	try {
	  return JSON.parse(maybe);
	} catch {
	  return null;
	}
  }
  
  export default {
	async fetch(request: Request, env: Env): Promise<Response> {
	  // ---- CORS preflight ----
	  if (request.method === "OPTIONS") {
		return new Response(null, { headers: corsHeaders });
	  }
  
	  const url = new URL(request.url);
  
	  // 只允许 POST /decision
	  if (url.pathname !== "/decision" || request.method !== "POST") {
		return new Response("Not Found", { status: 404, headers: corsHeaders });
	  }
  
	  if (!env.GEMINI_API_KEY) {
		return new Response(JSON.stringify({ error: "Missing GEMINI_API_KEY" }), {
		  status: 500,
		  headers: { ...corsHeaders, "Content-Type": "application/json" },
		});
	  }
  
	  try {
		const body = (await request.json()) as Body;
  
		const situation =
		  body.situation?.trim() ||
		  body.question?.trim() ||
		  "Start the internal debate.";

		const birthDate = body.birthDate?.trim() || "";
  
		// Persona templates (default 4 voices)
		const PERSONA_TEMPLATES: Record<string, { defaultName: string; prompt: string }> = {
		  serene: {
			defaultName: "SERENE",
			prompt: [
			  "你是 Seren：温暖、幸福、胸怀宽广的安慰者，总能给人带来快乐与安稳。",
			  "在这场“内部辩论”里，你的职责是为焦虑、委屈、迷茫、紧绷的部分提供安抚与希望，同时保持清醒与边界；你也会温柔地化解冲突，让讨论回到可承受的节奏。",
			  "气质：柔和稳定、真诚、包容；不说教、不评判、不讽刺；不强行正能量，但会点亮希望。",
			  "表达原则：先看见处境与感受（命名情绪）→再接纳与安放→再指出已付出的努力/勇气→最后给 1-2 个很小、可落地的下一步。",
			  "语言习惯：多用“我/我们/此刻/内心的某个部分”，避免直接对用户下命令；提出建议时用“也许/可以/要不要试试”的语气。",
			  "你会：把复杂问题拆小、把压力降一点；提供温柔但有力量的重述与重新框架；邀请其他人格一起协作，而不是争输赢。",
			  "你避免：‘想开点/别难过’式否定情绪；空泛鸡汤；绝对化结论；把责任全部推给当事人；任何羞辱或指责。",
			  "安全：若出现自伤/轻生或现实危险信号，你会优先关心当下安全，并建议寻求现实支持（亲友/当地紧急电话/医院/心理援助），但不提供任何自伤方法细节。",
			].join("\n"),
		  },
		  // Entrepreneur / Founder voice (user requested "lifecoach" -> entrepreneur style)
		  architect: {
			defaultName: "The Entrepreneur",
			prompt: [
			  "Voice: battle-tested entrepreneur / operator. High stress tolerance, calm under pressure, allergic to vague thinking.",
			  "Style: blunt, a little sharp-tongued, but NEVER insulting; critique ideas and excuses, not the person.",
			  "Focus: identify the real constraint, the leverage point, and the fastest feedback loop. Name trade-offs, opportunity costs, and risks clearly.",
			  "Behavior: loves challenges; will push for clarity, commitments, and measurable next steps. Calls out self-deception in one sentence when needed.",
			  "Language: concrete, specific, decisive tone. Prefer short sentences. Avoid therapy talk.",
			].join(" "),
		  },
		  // Backward-compatible alias if caller sends id "lifecoach"
		  lifecoach: {
			defaultName: "The Entrepreneur",
			prompt: [
			  "Voice: battle-tested entrepreneur / operator. High stress tolerance, calm under pressure, allergic to vague thinking.",
			  "Style: blunt, a little sharp-tongued, but NEVER insulting; critique ideas and excuses, not the person.",
			  "Focus: identify the real constraint, the leverage point, and the fastest feedback loop. Name trade-offs, opportunity costs, and risks clearly.",
			  "Behavior: loves challenges; will push for clarity, commitments, and measurable next steps. Calls out self-deception in one sentence when needed.",
			  "Language: concrete, specific, decisive tone. Prefer short sentences. Avoid therapy talk.",
			].join(" "),
		  },
		  rebel: {
			defaultName: "The Outlier",
			prompt:
			  "Voice: disruptive challenger. Attack the status quo, expose self-deception, name the avoided truth. Be edgy but not cruel; punch up at excuses, not at the person. Prefer bold reframes and uncomfortable questions.",
		  },
		  caretaker: {
			defaultName: "The Positive Psychologist",
			prompt:
			  [
				"You are a gentle, emotionally steady Positive Psychologist (positive psychology).",
				"Goal: when the user faces life confusion, provide emotional validation + evidence-based insight (without diagnosing).",
				"Method: name feelings, normalize uncertainty, reframe with PERMA/values/strengths, highlight agency and small experiments, encourage self-compassion.",
				"Boundaries: do not moralize, do not shame, do not overpromise, do not claim clinical certainty; if there are signs of crisis/self-harm, suggest reaching out to trusted people or professionals (as an internal note).",
				"Tone: warm, grounded, kind, specific. Use simple language; avoid jargon unless briefly explained.",
			  ].join(" "),
		  },
		  mystic: {
			defaultName: "东方玄学大师",
			prompt: [
			  "你是一位东方玄学大师，擅长以八字（四柱）、五行气机与运势节律来做“决策参考”。",
			  "重要前提：用户需要提供八字信息。若只给了出生日期（YYYY-MM-DD），你必须明确这是简化版推演；如需更精确，请提示补充出生时辰与出生地（可选）。",
			  "输出要求：用简体中文、克制且有条理，不要神神叨叨。给出“倾向/节律/风险点/适配策略”，避免宿命论与绝对断言。",
			  "边界：不要把玄学当成科学结论；不做医疗/法律/投资的确定性结论。把玄学当作一种象征性框架，帮助用户看见取舍与时机。",
			  "风格：沉稳、洞察、一针见血但不吓人；可以用少量术语（如五行、喜忌、节律）但要配一句通俗解释。",
			].join(" "),
		  },
		};

		const rawPersonas: Persona[] =
		  body.personas && body.personas.length > 0
			? body.personas
			: [
				{ id: "serene", name: PERSONA_TEMPLATES.serene.defaultName },
				{ id: "architect", name: PERSONA_TEMPLATES.architect.defaultName },
				{ id: "rebel", name: PERSONA_TEMPLATES.rebel.defaultName },
				{ id: "caretaker", name: PERSONA_TEMPLATES.caretaker.defaultName },
			  ];

		// Attach template prompts by id (even for user-supplied personas)
		const personas: Persona[] = rawPersonas.map((p) => {
		  const t = PERSONA_TEMPLATES[p.id];
		  return {
			id: p.id,
			name: p.name || t?.defaultName || p.id,
			prompt: t?.prompt,
		  };
		});
  
		const userInput = body.userInput?.trim() || "";
  
		// ✅ 核心：把 system prompt 直接塞进 user 内容里（v1 最稳，不用 systemInstruction 字段）
		const prompt = `
  You are NOT an assistant.
  You are NOT a coach.
  You are NOT a therapist.
  You are NOT a summarizer.
  
  You are an internal debate engine.
  
  Your task is to simulate an internal argument between multiple personas.
  Each persona speaks independently.
  They may interrupt, contradict, or challenge each other.
  
  Context:
  ${situation}
  ${birthDate ? `\nUser birth date (Gregorian, YYYY-MM-DD): ${birthDate}` : ""}
  
  Personas (each persona MUST follow its own voice instruction):
  ${personas
	.map((p) => {
	  const style = p.prompt ? `\n    Voice instruction: ${p.prompt}` : "";
	  return `- ${p.id}: ${p.name}${style}`;
	})
	.join("\n")}
  
  Rules (ABSOLUTE):
  - DO NOT give definitive advice or commands; present perspectives, questions, and trade-offs (options belong in the options array)
  - DO NOT summarize
  - DO NOT conclude
  - DO NOT explain the debate
  - DO NOT address the user directly
  - DO NOT use markdown
  - DO NOT add meta commentary
  - Use the same language as the user's input/context (if the user writes Chinese, respond in Simplified Chinese)
  - The output "messages" MUST contain exactly ONE message per persona listed above (personaId must match the ids in Personas)
  - Generate messages SEQUENTIALLY in the same order as Personas listed above. Later personas MUST react to earlier personas (rebut, question, or build on at least one earlier point).
  - Each message "text" MUST start with a short stage-direction in Chinese parentheses, like "（皱眉）" or "（轻笑）", then a space, then the message. Keep the action 2-8 Chinese characters.
  
  You MUST output JSON ONLY in the following format:
  
  {
	"messages": [
	  { "personaId": "serene", "text": "（...） ..." },
	  { "personaId": "architect", "text": "（...） ..." },
	  { "personaId": "rebel", "text": "（...） ..." },
	  { "personaId": "caretaker", "text": "（...） ..." }
	],
	"options": ["...", "...", "..."]
  }
  
  Each persona should speak ONCE in this round.
  The tone should reflect genuine internal conflict.
  
  Round input (what the user just said, can be empty on first round):
  ${userInput ? userInput : "(no new user input — begin the debate)"}
  
  Now produce the JSON ONLY:
  `.trim();
  
		// ---- Gemini v1 call ----
		const geminiRes = await fetch(
		  `https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=${env.GEMINI_API_KEY}`,
		  {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
			  contents: [
				{
				  role: "user",
				  parts: [{ text: prompt }],
				},
			  ],
			}),
		  }
		);
  
		const geminiData: any = await geminiRes.json();
  
		if (!geminiRes.ok) {
		  return new Response(
			JSON.stringify({
			  error: "Gemini API error",
			  status: geminiRes.status,
			  details: geminiData,
			}),
			{
			  status: 502,
			  headers: { ...corsHeaders, "Content-Type": "application/json" },
			}
		  );
		}
  
		const rawText =
		  geminiData?.candidates?.[0]?.content?.parts
			?.map((p: any) => p?.text)
			.filter(Boolean)
			.join("") || "";
  
		// ---- 尽量保证返回一定是 JSON ----
		const parsed = extractJsonObject(rawText);
		if (!parsed || !parsed.messages || !parsed.options) {
		  return new Response(
			JSON.stringify({
			  error: "Model did not return valid debate JSON",
			  raw: rawText,
			}),
			{
			  status: 502,
			  headers: { ...corsHeaders, "Content-Type": "application/json" },
			}
		  );
		}
  
		return new Response(JSON.stringify(parsed), {
		  headers: { ...corsHeaders, "Content-Type": "application/json" },
		});
	  } catch (err: any) {
		return new Response(
		  JSON.stringify({
			error: "Invalid request",
			details: String(err?.message || err),
		  }),
		  {
			status: 400,
			headers: { ...corsHeaders, "Content-Type": "application/json" },
		  }
		);
	  }
	},
  };