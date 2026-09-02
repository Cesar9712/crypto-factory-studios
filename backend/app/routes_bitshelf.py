from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
import secrets
import time
import zipfile
from typing import Callable

from fastapi import Header
from fastapi.responses import Response

CATALOG = {
    "bitshelf_free_starter": {"name":"Free AI Starter Pack","price":"0.00","category":"AI","summary":"10 practical prompts + a mini launch checklist.","free":True},
    "bitshelf_ai_prompt_starter": {"name":"50 AI Prompts for Daily Work","price":"2.00","category":"AI","summary":"Writing, planning, research and productivity prompts."},
    "bitshelf_social_calendar": {"name":"30-Day Social Content Calendar","price":"3.00","category":"Marketing","summary":"A ready-to-use 30-day content system."},
    "bitshelf_freelance_proposal": {"name":"Freelancer Proposal & Client Kit","price":"3.00","category":"Freelance","summary":"Proposal, scope, onboarding and delivery templates."},
    "bitshelf_budget_tracker": {"name":"Small Business Budget Tracker","price":"4.00","category":"Business","summary":"Revenue, expense and monthly planning templates."},
    "bitshelf_repurpose_kit": {"name":"Content Repurposing Kit","price":"4.00","category":"Marketing","summary":"Turn one idea into posts, emails and short-form scripts."},
    "bitshelf_game_design_prompts": {"name":"Game Design AI Prompt Pack","price":"5.00","category":"Game Dev","summary":"Prompts for mechanics, quests, balancing, UI and RPG systems."},
    "bitshelf_web3_starter": {"name":"Web3 Creator Starter Kit","price":"3.00","category":"Web3","summary":"Plain-language glossary, launch checklist and safety notes."},
    "bitshelf_creator_launch": {"name":"Creator Launch Checklist","price":"2.00","category":"Creator","summary":"A compact launch system for digital products."},
    "bitshelf_weekly_system": {"name":"Weekly Productivity System","price":"3.00","category":"Productivity","summary":"Weekly planning, review and priority templates."},
    "bitshelf_microstore_templates": {"name":"Microstore Starter Templates","price":"5.00","category":"Business","summary":"Product page, FAQ, offer and support templates."},
    "bitshelf_ai_creator_bundle": {"name":"AI Creator Bundle","price":"9.00","category":"Bundle","summary":"Prompts + social calendar + repurposing kit."},
    "bitshelf_freelancer_bundle": {"name":"Freelancer Business Bundle","price":"10.00","category":"Bundle","summary":"Proposal + budget + productivity + launch system."},
    "bitshelf_gamedev_bundle": {"name":"Game Dev Starter Bundle","price":"12.00","category":"Bundle","summary":"Game design + Web3 + creator launch resources."},
    "bitshelf_creator_vault": {"name":"Digital Creator Vault","price":"15.00","category":"Premium","summary":"The complete current BitShelf collection."},
}

BUNDLES = {
    "bitshelf_ai_creator_bundle":["bitshelf_ai_prompt_starter","bitshelf_social_calendar","bitshelf_repurpose_kit"],
    "bitshelf_freelancer_bundle":["bitshelf_freelance_proposal","bitshelf_budget_tracker","bitshelf_weekly_system","bitshelf_creator_launch"],
    "bitshelf_gamedev_bundle":["bitshelf_game_design_prompts","bitshelf_web3_starter","bitshelf_creator_launch"],
}
BUNDLES["bitshelf_creator_vault"]=[k for k,v in CATALOG.items() if not v.get("free") and k not in BUNDLES and k!="bitshelf_creator_vault"]

def _prompt_lines():
    jobs=["write a clear landing page","turn rough notes into a concise summary","create a 7-day action plan","find weak points in an offer","draft a helpful FAQ","generate 10 useful content angles","rewrite a message for clarity","build a simple decision matrix","create a customer onboarding checklist","turn a goal into measurable milestones"]
    contexts=["a solo creator","a freelancer","a small digital store","a game developer","a local service business"]
    out=[]
    n=1
    for context in contexts:
        for job in jobs:
            out.append(f"{n}. Act as a practical assistant for {context}. Help me {job}. Ask only for information that materially changes the result. Return a finished draft plus 3 concrete improvements.")
            n+=1
    return "\n\n".join(out)

def _files_for(product_id: str) -> dict[str,str]:
    if product_id=="bitshelf_free_starter":
        return {
            "README.md":"# BitShelf Free AI Starter\n10 practical prompts and a compact launch checklist. Use and adapt these for your own work. Do not resell this file unchanged.",
            "10-prompts.md":"\n\n".join(_prompt_lines().split("\n\n")[:10]),
            "launch-checklist.txt":"Define one buyer problem\nCreate one clear offer\nSet one simple price\nPrepare one delivery file\nWrite one benefit-led product page\nTest the checkout\nPublish one useful educational post\nReview results after 7 days\n",
        }
    if product_id=="bitshelf_ai_prompt_starter":
        return {"README.md":"# 50 AI Prompts for Daily Work\nOriginal practical prompts for commercial or personal internal use. Do not redistribute the pack unchanged.","50-ai-prompts.md":_prompt_lines()}
    if product_id=="bitshelf_social_calendar":
        rows=["day,goal,format,prompt,cta"]
        goals=["educate","build trust","show process","solve objection","demonstrate result","share checklist"]
        formats=["short post","carousel","short video","thread","email","image post"]
        for i in range(1,31):
            g=goals[(i-1)%len(goals)]; f=formats[(i-1)%len(formats)]
            rows.append(f'{i},{g},{f},"Create one useful {f} that helps the audience {g}. Include one specific example.","Save this / learn more"')
        return {"README.md":"# 30-Day Social Content Calendar\nEdit the CSV in Sheets, Excel or any spreadsheet app.","30-day-calendar.csv":"\n".join(rows),"content-rules.md":"Lead with one problem. Teach one idea. Use one example. End with one low-pressure CTA. Avoid spam and unsupported claims."}
    if product_id=="bitshelf_freelance_proposal":
        return {
            "README.md":"# Freelancer Proposal & Client Kit\nReusable originals for service work.",
            "proposal-template.md":"# Proposal\n## Client goal\n[What outcome matters?]\n## Scope\n- Deliverable 1\n- Deliverable 2\n## Timeline\n[Dates/milestones]\n## Price\n[Amount + payment terms]\n## Included revisions\n[Number/scope]\n## Not included\n[Explicit exclusions]\n## Acceptance\nApproval confirms scope, price and timeline.",
            "client-onboarding.md":"1. Confirm goal and success metric.\n2. Collect source materials.\n3. Confirm contact person.\n4. Confirm deadline and review window.\n5. Record scope changes in writing.\n6. Deliver with a summary and next steps.",
            "delivery-email.md":"Subject: Your project is ready\n\nHi [Name],\nYour agreed deliverables are ready here: [link].\nIncluded: [items].\nPlease send any in-scope feedback by [date].\nThanks,\n[Name]",
        }
    if product_id=="bitshelf_budget_tracker":
        return {
            "README.md":"# Small Business Budget Tracker\nOpen the CSV files in Excel, Google Sheets or LibreOffice.",
            "monthly-budget.csv":"category,budgeted,actual,difference\nSales,0,0,=C2-B2\nSoftware,0,0,=C3-B3\nMarketing,0,0,=C4-B4\nContractors,0,0,=C5-B5\nFees,0,0,=C6-B6\nOther,0,0,=C7-B7",
            "cashflow.csv":"date,description,type,amount,notes\nYYYY-MM-DD,Example,income,0,\nYYYY-MM-DD,Example,expense,0,",
            "monthly-review.md":"Revenue this month:\nTop expense:\nRecurring cost to review:\nCash reserve:\nOne cost to cut:\nOne revenue action for next month:",
        }
    if product_id=="bitshelf_repurpose_kit":
        return {
            "README.md":"# Content Repurposing Kit",
            "workflow.md":"Start with one useful source idea. Extract: 1 core claim, 3 supporting points, 1 example, 1 objection, 1 next action. Then create: one long post, three short posts, one email, one 45-second video script and one FAQ answer.",
            "repurpose-prompts.md":"1. Turn this source into a concise educational post with one example.\n2. Extract 5 short standalone insights without clickbait.\n3. Convert the source into a 45-second spoken script.\n4. Write a helpful email that teaches the main idea before mentioning the offer.\n5. Identify the strongest objection and answer it factually.\n6. Create a carousel outline: hook, 5 teaching slides, recap, CTA.",
        }
    if product_id=="bitshelf_game_design_prompts":
        return {
            "README.md":"# Game Design AI Prompt Pack\nUse as ideation and design aids; validate ideas in playtests.",
            "game-design-prompts.md":"\n\n".join([
                "Design a core loop for a 10-minute mobile RPG session. Specify action, reward, progression and return trigger without pay-to-win pressure.",
                "Create 12 quest concepts that reuse existing locations but change objectives, enemy composition or narrative context.",
                "Audit this combat system for dominant strategies, dead choices and unclear feedback. Return fixes ordered by impact.",
                "Design a branching talent tree with three distinct playstyles and meaningful tradeoffs. Avoid mandatory nodes.",
                "Create a loot rarity system with readable stat ranges, duplicate handling and bad-luck protection.",
                "Design a boss with three phases where each phase teaches then tests one mechanic.",
                "Create 20 enemy variants from 5 base archetypes using stats, skills and presentation rather than entirely new assets.",
                "Review this HUD for mobile thumb reach, visual hierarchy and combat readability.",
                "Propose a crafting economy with useful sinks, controlled inflation and clear recipes.",
                "Design an energy system that limits abuse without punishing normal play.",
                "Create 15 achievement ideas that reward mastery, exploration and experimentation rather than pure grinding.",
                "Build a balancing checklist for damage, healing, cooldowns, critical chance and resource generation.",
            ])
        }
    if product_id=="bitshelf_web3_starter":
        return {
            "README.md":"# Web3 Creator Starter Kit\nEducational material only; not investment advice.",
            "glossary.md":"Wallet: software used to manage blockchain addresses and signatures.\nPublic address: shareable destination for assets.\nPrivate key/seed phrase: secret credentials; never share them.\nGas: network fee for a transaction.\nStablecoin: token designed to track a reference asset such as USD.\nSmart contract: code deployed to a blockchain.\nTransaction hash: public identifier for a blockchain transaction.\nConfirmation: evidence that a transaction has been included in the chain.",
            "launch-checklist.md":"Choose one network.\nDocument exact token contract.\nNever request user seed phrases.\nVerify recipient, contract, amount and chain server-side.\nPrevent transaction-hash reuse.\nSeparate testnet and mainnet.\nFail closed when RPC/provider data is unavailable.\nPublish clear network warnings.",
        }
    if product_id=="bitshelf_creator_launch":
        return {"README.md":"# Creator Launch Checklist","launch.md":"Problem defined\nSpecific buyer defined\nDeliverable finished\nPrice set\nProduct page written\nCheckout tested\nDelivery tested\nRefund/licence terms visible\nOne free sample prepared\nThree educational launch posts prepared\nAnalytics event for purchase enabled\nSeven-day review date scheduled"}
    if product_id=="bitshelf_weekly_system":
        return {"README.md":"# Weekly Productivity System","weekly-plan.md":"# Week of [date]\n## One outcome that matters\n\n## Top 3 results\n1.\n2.\n3.\n## Tasks to delete/defer\n\n## Risks/blockers\n\n## Friday review\nWhat shipped?\nWhat stalled?\nWhat should change next week?","daily-focus.csv":"day,one_priority,secondary_task,blocked_by,done\nMonday,,,,\nTuesday,,,,\nWednesday,,,,\nThursday,,,,\nFriday,,,,"}
    if product_id=="bitshelf_microstore_templates":
        return {
            "README.md":"# Microstore Starter Templates",
            "product-page.md":"# [Product name]\n**One-sentence outcome**\n\n## What it helps you do\n[3 benefits]\n\n## Included\n[files/items]\n\n## Who it is for\n[specific buyer]\n\n## Format\n[file types]\n\n## Licence\n[usage terms]\n\n## FAQ\n[compatibility, delivery, support]",
            "faq.md":"How do I receive my files? — Automatically after confirmed payment.\nCan I share the download link? — No; links are personal and temporary.\nWhat software do I need? — Listed on each product page.\nDo you offer support? — Support covers delivery and file-access issues.",
            "support-replies.md":"PAYMENT PENDING: We have not yet verified the transaction. Confirm network, token and transaction hash.\nLINK EXPIRED: Request a fresh download link from your purchase page.\nFILE ISSUE: Tell us the filename and the app you are opening it with.",
        }
    return {"README.md":"BitShelf digital product."}

def _all_files(product_id: str) -> dict[str,str]:
    children=BUNDLES.get(product_id)
    if not children:
        return _files_for(product_id)
    out={"README.md":f"# {CATALOG[product_id]['name']}\nThis bundle contains the listed BitShelf resources."}
    for child in children:
        for name,body in _files_for(child).items():
            out[f"{child}/{name}"]=body
    return out

def _zip_bytes(product_id: str) -> bytes:
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name,body in _all_files(product_id).items():
            z.writestr(name,body)
        z.writestr("LICENSE.txt","BitShelf licence: You may use and adapt these files for your own personal or commercial projects and client work. You may not resell, redistribute, sublicense or publish the original files or a trivially modified copy as a competing template/product pack. No warranty is provided.")
    return out.getvalue()

def _secret(settings) -> bytes:
    raw=os.getenv("BITSHELF_DOWNLOAD_SECRET","").strip() or settings.owner_bootstrap_token
    if not raw:
        raise RuntimeError("download_secret_missing")
    return raw.encode()

def _encode_ticket(settings,user_id: str,product_id: str,ttl: int=900) -> str:
    payload={"u":user_id,"p":product_id,"e":int(time.time())+ttl,"n":secrets.token_hex(8)}
    raw=json.dumps(payload,separators=(",",":"),sort_keys=True).encode()
    sig=hmac.new(_secret(settings),raw,hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw+sig).decode().rstrip("=")

def _decode_ticket(settings,token: str) -> dict:
    padded=token+"="*((4-len(token)%4)%4)
    blob=base64.urlsafe_b64decode(padded.encode())
    if len(blob)<33:
        raise ValueError("invalid_ticket")
    raw,sig=blob[:-32],blob[-32:]
    expected=hmac.new(_secret(settings),raw,hashlib.sha256).digest()
    if not hmac.compare_digest(sig,expected):
        raise ValueError("invalid_ticket")
    data=json.loads(raw.decode())
    if int(data.get("e",0))<int(time.time()):
        raise ValueError("expired_ticket")
    return data

def register_bitshelf_routes(app, *, db, settings, session_user: Callable, fail: Callable):
    @app.get("/api/v1/bitshelf/catalog")
    def catalog():
        return {"products":[{"product_id":k,**v} for k,v in CATALOG.items()]}

    @app.get("/api/v1/bitshelf/free/{product_id}")
    def free_download(product_id: str):
        item=CATALOG.get(product_id)
        if not item or not item.get("free"):
            fail("product_not_found","Free product not found",404)
        return Response(_zip_bytes(product_id),media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="{product_id}.zip"',"Cache-Control":"no-store"})

    @app.post("/api/v1/bitshelf/download-ticket/{product_id}")
    def download_ticket(product_id: str, authorization: str | None=Header(default=None)):
        user,_=session_user(authorization)
        item=CATALOG.get(product_id)
        if not item or item.get("free"):
            fail("product_not_found","Paid product not found",404)
        purchase=db.one("SELECT purchase_id FROM purchase_history WHERE user_id=? AND product_id=? ORDER BY created_at DESC",(user["id"],product_id))
        if not purchase:
            fail("purchase_required","Confirmed purchase required",403)
        token=_encode_ticket(settings,user["id"],product_id)
        return {"download_url":f"/api/v1/bitshelf/download/{token}","expires_in":900}

    @app.get("/api/v1/bitshelf/download/{token}")
    def paid_download(token: str, authorization: str | None=Header(default=None)):
        user,_=session_user(authorization)
        try:
            ticket=_decode_ticket(settings,token)
        except Exception as exc:
            fail("invalid_download_link",str(exc),403)
        if ticket.get("u")!=user["id"]:
            fail("download_owner_mismatch","This download link belongs to another account",403)
        product_id=str(ticket.get("p") or "")
        purchase=db.one("SELECT purchase_id FROM purchase_history WHERE user_id=? AND product_id=? ORDER BY created_at DESC",(user["id"],product_id))
        if not purchase:
            fail("purchase_required","Confirmed purchase required",403)
        return Response(_zip_bytes(product_id),media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="{product_id}.zip"',"Cache-Control":"no-store"})
