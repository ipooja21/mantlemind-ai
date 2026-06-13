import os
import json
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [Agent7] %(message)s")


class LLMIntelligenceAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

        if self.api_key:
            logging.info("Groq API key loaded ✓ (len=%d)", len(self.api_key))
        else:
            logging.warning("No Groq key — fallback mode")

    def _call_groq(self, prompt: str, max_tokens: int = 250) -> str:
        
        if not self.api_key:
            return ""
        try:
            resp = requests.post(
                self.url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"]
                logging.info("Groq response OK ✓")
                return text.strip()
            else:
                logging.warning("Groq %d: %s", resp.status_code, resp.text[:100])
                return ""
        except Exception as e:
            logging.error("Groq error: %s", e)
            return ""

    def generate_insight(
        self,
        alpha_result:      dict,
        whale_count:       int   = 0,
        anomaly_count:     int   = 0,
        tx_count:          int   = 0,
        top_anomaly_score: float = 0.0,
    ) -> str:
        prompt = f"""You are an expert on-chain analyst for the Mantle blockchain network.
Analyze this real-time intelligence data and provide a concise, actionable insight:

LIVE DATA:
- Alpha Score:          {alpha_result.get('alpha_score', 0)}/100
- Market Signal:        {alpha_result.get('signal', 'NEUTRAL')}
- Transactions:         {tx_count}
- Whale wallets active: {whale_count}
- Anomalies detected:   {anomaly_count}
- Top anomaly score:    {top_anomaly_score:.2f}

Write exactly 3 sentences:
1. Current market condition on Mantle Network
2. Key risk or opportunity right now
3. Specific actionable recommendation for traders

Max 90 words. Be specific to Mantle. Sound professional."""

        result = self._call_groq(prompt, max_tokens=250)
        if result:
            return result
        return self._fallback_insight(alpha_result, whale_count, anomaly_count)

    def chat_with_data(self, user_question: str, context: dict) -> str:
        if not self.api_key:
            return "Set GROQ_API_KEY in .env to enable AI chat!"

        prompt = f"""You are MantleMind AI — an intelligent assistant for Mantle blockchain analysis.

Current live analysis context:
{json.dumps(context, indent=2)}

User question: {user_question}

Answer in 2-3 sentences. Be specific, helpful, and professional. Reference the actual numbers from the context."""

        result = self._call_groq(prompt, max_tokens=200)
        if result:
            return result
        return "Groq API error — check your API key or try again."

    def analyze(
        self,
        alpha_score: float = 50,
        signal: str = "NEUTRAL",
        whale_count: int = 0,
        anom_count: int = 0,
        anom_rate: float = 0.0,
        tx_count: int = 0,
        volume: float = 0.0,
    ) -> str:
        
        return self.generate_insight(
            alpha_result={"alpha_score": alpha_score, "signal": signal},
            whale_count=whale_count,
            anomaly_count=anom_count,
            tx_count=tx_count,
            top_anomaly_score=anom_rate / 100,
        )

    def _fallback_insight(self, alpha_result, whale_count, anomaly_count):
        score  = alpha_result.get("alpha_score", 50)
        signal = alpha_result.get("signal", "NEUTRAL")

        if score >= 75:
            market = "Mantle network showing strong bullish momentum with elevated on-chain activity"
            action = "Consider monitoring key DeFi protocols for entry opportunities"
        elif score >= 55:
            market = "Mantle network displaying moderate bullish signals with steady transaction flow"
            action = "Watch whale wallet movements for directional confirmation"
        elif score >= 45:
            market = "Mantle network in consolidation phase with mixed on-chain signals"
            action = "Maintain current positions and monitor anomaly patterns closely"
        else:
            market = "Caution signals detected on Mantle network with elevated risk indicators"
            action = "Risk management advised — consider reducing exposure until signals clarify"

        risk = (
            f"{anomaly_count} anomalies flagged requiring attention."
            if anomaly_count > 0
            else "No significant anomalies detected in this window."
        )
        whale_note = (
            f"{whale_count} whale wallets showing active movement."
            if whale_count > 0
            else "No whale activity detected in current scan."
        )
        return f"{market}. {risk} {whale_note} {action}."