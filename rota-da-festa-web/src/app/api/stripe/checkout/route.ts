import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";

function getStripe() {
  return new Stripe(process.env.STRIPE_SECRET_KEY!, {
    apiVersion: "2025-01-27.acacia" as Stripe.LatestApiVersion,
  });
}

const PLANS: Record<string, { name: string; price: number; features: string[] }> = {
  basico: { name: "Básico", price: 1000, features: ["Pin no mapa", "Nome + telefone"] },
  destaque: { name: "Destaque", price: 2000, features: ["Pin no mapa", "Banner no evento", "Cupão desconto"] },
  premium: { name: "Premium", price: 3500, features: ["Tudo do Destaque", "Notificação push"] },
};

// POST /api/stripe/checkout — create Stripe Checkout session
export async function POST(req: NextRequest) {
  try {
    const { plan, businessName, email } = await req.json();
    const planInfo = PLANS[plan];

    if (!planInfo) {
      return NextResponse.json({ error: "Plano inválido" }, { status: 400 });
    }

    if (!process.env.STRIPE_SECRET_KEY) {
      return NextResponse.json({ error: "Stripe not configured. Set STRIPE_SECRET_KEY." }, { status: 500 });
    }

    const stripe = getStripe();
    const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://rotadafesta.vercel.app";

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      mode: "subscription",
      customer_email: email,
      metadata: { plan, businessName },
      line_items: [
        {
          price_data: {
            currency: "eur",
            product_data: {
              name: `Rota da Festa — Plano ${planInfo.name}`,
              description: planInfo.features.join(" · "),
            },
            unit_amount: planInfo.price,
            recurring: { interval: "month" },
          },
          quantity: 1,
        },
      ],
      success_url: `${baseUrl}/negocios?success=true`,
      cancel_url: `${baseUrl}/negocios?cancelled=true`,
    });

    return NextResponse.json({ url: session.url });
  } catch (e: any) {
    console.error("Stripe error:", e);
    return NextResponse.json({ error: e.message || "Erro ao criar sessão" }, { status: 500 });
  }
}
