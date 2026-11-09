import { motion, useReducedMotion } from "motion/react";
import { Clapperboard } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { timecode } from "@/lib/format";
import { useAuth } from "@/stores/auth";

const STEPS = [
  { title: "Give it a subject", body: "One line is enough: “The disappearance of the Roanoke colony.” Pick a length, a format and a voice." },
  { title: "The Story Director writes", body: "It researches the topic, drafts six alternative hooks, writes narration to length and lists every factual claim it makes." },
  { title: "Every scene gets directed", body: "Each scene gets a visual type, a camera move, atmosphere, a transition, sound effects and a music cue that suits what is being said." },
  { title: "Voice, captions, render", body: "Kokoro voices the script, Whisper times every word, and the engine animates, mixes and exports an MP4." },
  { title: "Edit one scene, not the whole video", body: "Rewrite a line or swap an image and only that scene is rebuilt. Everything else is reused." },
];

const VISUALS = [
  { still: "/demo/still-map.jpg", name: "Animated maps", body: "Places are geocoded offline and journeys draw themselves across the region." },
  { still: "/demo/still-timeline.jpg", name: "Timelines", body: "Dates from the narration become a chronology the camera travels along." },
  { still: "/demo/still-parallax.jpg", name: "2.5D parallax", body: "Stills are split into depth layers so landscapes move like a camera dolly." },
  { still: "/demo/still-newspaper.jpg", name: "Archival front pages", body: "Reported events become a period front page with halftone photography." },
  { still: "/demo/still-portrait.jpg", name: "Character portraits", body: "People in the story get a portrait with a slow push-in and a name card." },
  { still: "/demo/still-kinetic.jpg", name: "Kinetic type", body: "Revelations and quotes land as full-frame typography." },
];

const FEATURES = [
  { name: "Story DNA", body: "Save a channel’s look, voice, captions, palette and music once. Every new video and series inherits it." },
  { name: "Hook Lab", body: "Six opening lines in different registers — question, mystery, shock — and you choose which one the story is built around." },
  { name: "Fact checker", body: "Claims are checked against encyclopedia sources and flagged as supported, contradicted or not found, with links." },
  { name: "Series Factory", body: "Plan ten connected episodes with a shared series bible, then produce them in a queue. One failure never stops the rest." },
  { name: "Runs on your machine", body: "Local models for writing, images, voice and transcription. No credits, no watermark, no upload of your ideas." },
  { name: "Honest about quality", body: "When an AI service is offline, ReelForge tells you which one, falls back where it can and labels what it substituted." },
];

const FAQ = [
  { q: "Is it really free?", a: "There are no plans, credits or paywalls. It runs on open-source models on your own computer. If you host it online, the free tiers of those providers have storage and traffic limits; the docs list them." },
  { q: "Do I need a graphics card?", a: "No. Everything runs on a CPU, slower. On an 8-core desktop CPU we measured about 6 minutes to write the story and storyboard, about 2 minutes per AI image, and under 4 minutes to voice, animate and encode a 45-second video. An NVIDIA GPU makes images take seconds instead." },
  { q: "Can I publish the videos commercially?", a: "Generally yes. The voice (Kokoro) and language model (Qwen) are Apache-2.0. Images come from Stable Diffusion 1.5, whose OpenRAIL-M licence forbids certain harmful uses; you agree to those terms when you generate images. Music and sound effects are synthesised by ReelForge and are royalty-free." },
  { q: "Will this make my videos go viral?", a: "Nobody can promise that. ReelForge helps you test hooks, pace the story and keep a consistent look, which is what you control." },
  { q: "How accurate are the facts?", a: "The Story Director is told never to invent facts, and educational claims are checked against sources. Small local models still make mistakes, so review anything flagged before you publish." },
];

function HeroReel() {
  const video = useRef<HTMLVideoElement>(null);
  const [t, setT] = useState(0);
  const reduce = useReducedMotion();
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    const tick = () => setT(v.currentTime);
    v.addEventListener("timeupdate", tick);
    if (reduce) v.pause();
    return () => v.removeEventListener("timeupdate", tick);
  }, [reduce]);
  return (
    <motion.figure
      initial={reduce ? false : { opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.9, ease: [0.2, 0.7, 0.2, 1] }}
      className="relative mx-auto w-full max-w-[340px]"
    >
      <div className="beam-glow pointer-events-none absolute -inset-24 -z-10" aria-hidden />
      <div className="frame-916 overflow-hidden rounded-[22px] border border-line-strong bg-surface shadow-[0_40px_120px_-30px_rgba(91,63,217,0.55)]">
        <video
          ref={video}
          src="/demo/reel.mp4"
          poster="/demo/poster.jpg"
          className="size-full object-cover"
          autoPlay={!reduce}
          muted
          loop
          playsInline
          aria-label="A short documentary about the lost Roanoke colony, made with ReelForge"
        />
      </div>
      <figcaption className="mt-3 flex items-center justify-between gap-4 text-xs text-faint">
        <span>Made with ReelForge, script edited by hand</span>
        <span className="timecode">{timecode(t)}</span>
      </figcaption>
    </motion.figure>
  );
}

export default function LandingPage() {
  const status = useAuth((s) => s.status);
  const signedIn = status === "authenticated";
  return (
    <div className="overflow-x-clip">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 md:px-8">
        <span className="flex items-center gap-2 font-heading text-lg font-semibold">
          <Clapperboard className="size-5 text-uv" aria-hidden /> ReelForge
        </span>
        <nav className="flex items-center gap-2" aria-label="Account">
          {signedIn ? (
            <Button asChild><Link to="/app">Open studio</Link></Button>
          ) : (
            <>
              <Button asChild variant="ghost"><Link to="/login">Sign in</Link></Button>
              <Button asChild><Link to="/register">Create account</Link></Button>
            </>
          )}
        </nav>
      </header>

      <main id="main">
        <section className="mx-auto grid max-w-6xl items-center gap-14 px-4 pb-24 pt-10 md:grid-cols-[1.15fr_1fr] md:px-8 md:pt-16">
          <div>
            <h1 className="text-5xl font-semibold leading-[0.98] md:text-7xl">Turn any idea into a cinematic story.</h1>
            <p className="mt-6 max-w-[34rem] text-lg text-subtle">
              ReelForge researches your subject, writes the narration, directs every scene, voices it and renders a finished
              vertical video. It runs on your own computer, so there are no credits to run out.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg"><Link to={signedIn ? "/create" : "/register"}>Make your first video</Link></Button>
              <Button asChild size="lg" variant="outline"><a href="#how">See how it works</a></Button>
            </div>
            <dl className="mt-12 grid max-w-md grid-cols-3 gap-6 border-t border-line pt-6 text-sm">
              <div><dt className="text-faint">Formats</dt><dd className="mt-1 text-text">9:16, 16:9, 1:1</dd></div>
              <div><dt className="text-faint">Lengths</dt><dd className="mt-1 text-text">30 to 90 s</dd></div>
              <div><dt className="text-faint">Export</dt><dd className="mt-1 text-text">1080p MP4</dd></div>
            </dl>
          </div>
          <HeroReel />
        </section>

        <section id="how" className="border-t border-line bg-surface/40">
          <div className="mx-auto max-w-6xl px-4 py-20 md:px-8">
            <h2 className="max-w-xl text-3xl font-semibold md:text-4xl">From one sentence to a finished reel</h2>
            <ol className="mt-12 grid gap-x-10 gap-y-10 md:grid-cols-2 lg:grid-cols-3">
              {STEPS.map((step, i) => (
                <li key={step.title} className="grid grid-cols-[2.25rem_1fr] gap-3">
                  <span className="timecode pt-0.5 text-sm">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <h3 className="text-lg font-semibold">{step.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-subtle">{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-20 md:px-8">
          <div className="grid gap-4 md:grid-cols-[1fr_1.4fr] md:items-end">
            <h2 className="text-3xl font-semibold md:text-4xl">Visuals chosen for the story, not a slideshow</h2>
            <p className="text-subtle">
              A sentence about a voyage becomes a map. A list of dates becomes a timeline. The Story Director picks the visual
              that explains each moment, and the engine animates it. These stills are from the video above.
            </p>
          </div>
          <div className="mt-12 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
            {VISUALS.map((v) => (
              <figure key={v.name}>
                <img src={v.still} alt="" loading="lazy" className="frame-916 w-full rounded-lg border border-line object-cover" />
                <figcaption className="mt-3">
                  <p className="text-sm font-semibold">{v.name}</p>
                  <p className="mt-1 text-xs leading-relaxed text-subtle">{v.body}</p>
                </figcaption>
              </figure>
            ))}
          </div>
        </section>

        <section className="border-y border-line bg-surface/40">
          <div className="mx-auto grid max-w-6xl gap-x-12 gap-y-10 px-4 py-20 md:grid-cols-3 md:px-8">
            {FEATURES.map((f) => (
              <div key={f.name}>
                <h3 className="text-lg font-semibold">{f.name}</h3>
                <p className="mt-2 text-sm leading-relaxed text-subtle">{f.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-3xl px-4 py-20 md:px-8">
          <h2 className="text-3xl font-semibold">Questions</h2>
          <div className="mt-8 divide-y divide-line border-y border-line">
            {FAQ.map((item) => (
              <details key={item.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-left font-medium">
                  {item.q}
                  <span className="text-uv transition-transform group-open:rotate-45" aria-hidden>+</span>
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-subtle">{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 pb-24 md:px-8">
          <div className="flex flex-wrap items-center justify-between gap-6 rounded-2xl border border-line bg-surface px-8 py-10">
            <div>
              <h2 className="text-2xl font-semibold">Your next video starts with a sentence.</h2>
              <p className="mt-2 text-subtle">Create an account on this ReelForge installation to start.</p>
            </div>
            <Button asChild size="lg"><Link to={signedIn ? "/create" : "/register"}>Start creating</Link></Button>
          </div>
        </section>
      </main>
      <footer className="border-t border-line px-4 py-8 text-center text-xs text-faint md:px-8">
        ReelForge AI · Open-source software. Generated media is subject to the licences listed in the documentation.
      </footer>
    </div>
  );
}
