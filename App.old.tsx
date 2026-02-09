
import React, { useState, useEffect, useRef } from 'react';
import { 
  ChevronRight, 
  MapPin, 
  Sparkles, 
  Menu, 
  X, 
  Instagram, 
  Facebook, 
  Linkedin, 
  MessageCircle, 
  Send, 
  Loader2, 
  Mic, 
  MicOff, 
  Phone, 
  ArrowUpRight,
  ChevronDown,
  Play,
  Maximize2,
  FileText,
  CheckCircle2,
  Image as ImageIcon,
  Clock,
  UtensilsCrossed,
  Palette
} from 'lucide-react';
import { GoogleGenAI, Modality, LiveServerMessage } from "@google/genai";
import { VENUES, SERVICES } from './constants';

// --- Audio Encoding/Decoding Utilities ---
function encode(bytes: Uint8Array) {
  let binary = '';
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function decode(base64: string) {
  const binaryString = atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

async function decodeAudioData(
  data: Uint8Array,
  ctx: AudioContext,
  sampleRate: number,
  numChannels: number,
): Promise<AudioBuffer> {
  const dataInt16 = new Int16Array(data.buffer);
  const frameCount = dataInt16.length / numChannels;
  const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);

  for (let channel = 0; channel < numChannels; channel++) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < frameCount; i++) {
      channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
    }
  }
  return buffer;
}

// --- ChatBot Component ---
interface ChatBotProps {
  isOpen: boolean;
  setIsOpen: (val: boolean) => void;
}

const ChatBot: React.FC<ChatBotProps> = ({ isOpen, setIsOpen }) => {
  const [messages, setMessages] = useState<{ role: 'user' | 'model'; text: string }[]>([
    { role: 'model', text: "Hi! Welcome to Natasha Mae's Enterprise. I'm Jessica, your booking concierge. I'd love to help you book a VIP Tour!" }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  
  const scrollRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<any>(null);
  const audioContextRef = useRef<{ input: AudioContext; output: AudioContext } | null>(null);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const nextStartTimeRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);

  const systemInstruction = `You are Jessica, the Booking Concierge for Natasha Mae's Enterprise.
Personality: Elegant, warm, polished, and professional. 
Company Tagline: "Where we create unforgettable memories."
Promote VIP Tours at all times. Use the provided venue data (The Vault, Mae's Liberty Palace, Banquet Facility) to guide users.
CRITICAL: When the session starts, immediately introduce yourself verbally and offer a VIP tour. Do not wait for the user to speak first if you can.`;

  // --- Auto-start Voice Session when Opened ---
  useEffect(() => {
    if (isOpen) {
      startVoiceSession();
    } else {
      stopVoiceSession();
    }
  }, [isOpen]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

  const stopVoiceSession = () => {
    if (sessionRef.current) { sessionRef.current.close(); sessionRef.current = null; }
    if (streamRef.current) { streamRef.current.getTracks().forEach(track => track.stop()); streamRef.current = null; }
    for (const source of sourcesRef.current) source.stop();
    sourcesRef.current.clear();
    setIsVoiceActive(false);
  };

  const startVoiceSession = async () => {
    if (isVoiceActive) return;
    try {
      setIsVoiceActive(true);
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY as string });
      
      if (!audioContextRef.current) {
        audioContextRef.current = {
          input: new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 }),
          output: new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 })
        };
      }
      
      const { input: inputCtx, output: outputCtx } = audioContextRef.current;
      
      // Resume contexts if they are suspended (browser policy)
      if (inputCtx.state === 'suspended') await inputCtx.resume();
      if (outputCtx.state === 'suspended') await outputCtx.resume();

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        callbacks: {
          onopen: () => {
            console.log("Jessica is ready...");
            const source = inputCtx.createMediaStreamSource(stream);
            const scriptProcessor = inputCtx.createScriptProcessor(4096, 1, 1);
            scriptProcessor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              const int16 = new Int16Array(inputData.length);
              for (let i = 0; i < inputData.length; i++) int16[i] = inputData[i] * 32768;
              const pcmBlob = { data: encode(new Uint8Array(int16.buffer)), mimeType: 'audio/pcm;rate=16000' };
              sessionPromise.then(session => {
                if (session) session.sendRealtimeInput({ media: pcmBlob });
              });
            };
            source.connect(scriptProcessor);
            scriptProcessor.connect(inputCtx.destination);
          },
          onmessage: async (message: LiveServerMessage) => {
            const base64Audio = message.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (base64Audio) {
              nextStartTimeRef.current = Math.max(nextStartTimeRef.current, outputCtx.currentTime);
              const audioBuffer = await decodeAudioData(decode(base64Audio), outputCtx, 24000, 1);
              const source = outputCtx.createBufferSource();
              source.buffer = audioBuffer;
              source.connect(outputCtx.destination);
              source.start(nextStartTimeRef.current);
              nextStartTimeRef.current += audioBuffer.duration;
              sourcesRef.current.add(source);
            }
          },
          onerror: (e) => {
            console.error("Jessica encountered an error:", e);
            setIsVoiceActive(false);
          },
          onclose: () => {
            console.log("Jessica's line is closed.");
            setIsVoiceActive(false);
          },
        },
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } } },
          systemInstruction,
        }
      });
      sessionRef.current = await sessionPromise;
    } catch (error) { 
      console.error("Microphone access or connection failed:", error);
      setIsVoiceActive(false); 
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setIsLoading(true);
    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY as string });
      const chat = ai.chats.create({ model: 'gemini-3-pro-preview', config: { systemInstruction } });
      const response = await chat.sendMessage({ message: userMsg });
      setMessages(prev => [...prev, { role: 'model', text: response.text || "I'd be happy to discuss our pricing tiers and availability with you!" }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'model', text: "I'm experiencing a minor connection issue, but you can reach us directly at 267-655-0230." }]);
    } finally { setIsLoading(false); }
  };

  return (
    <>
      <button 
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-6 right-6 z-[100] h-14 pl-5 pr-6 bg-emerald-900 text-white rounded-full flex items-center gap-3 shadow-[0_10px_40px_rgba(0,0,0,0.4)] hover:bg-emerald-800 transition-all ${isOpen ? 'hidden' : 'flex'}`}
      >
        <MessageCircle className="w-6 h-6 animate-pulse" />
        <span className="text-[10px] uppercase tracking-[0.2em] font-bold">Talk to Assistant</span>
      </button>

      {isOpen && (
        <div className="fixed bottom-6 right-6 z-[110] w-[350px] md:w-[420px] h-[650px] bg-white rounded-3xl shadow-[0_32px_64px_rgba(0,0,0,0.3)] border border-stone-100 flex flex-col overflow-hidden animate-fadeInUp">
          <div className="bg-emerald-950 p-6 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-emerald-900 flex items-center justify-center relative overflow-hidden">
                {isVoiceActive && <div className="absolute inset-0 border-2 border-emerald-400 rounded-full animate-ping opacity-50"></div>}
                <span className="font-serif italic text-white font-bold text-xl">J</span>
              </div>
              <div>
                <h4 className="text-white font-serif text-lg leading-tight font-bold">Jessica</h4>
                <div className="flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${isVoiceActive ? 'bg-emerald-400 animate-pulse' : 'bg-stone-500'}`}></span>
                  <p className="text-emerald-400 text-[9px] uppercase tracking-[0.2em] font-bold">
                    {isVoiceActive ? 'Listening...' : 'Connecting...'}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => isVoiceActive ? stopVoiceSession() : startVoiceSession()} 
                className={`p-2.5 rounded-xl transition-all duration-300 ${isVoiceActive ? 'bg-emerald-500 text-white shadow-[0_0_15px_rgba(16,185,129,0.4)]' : 'bg-white/5 text-white/70'}`}
                title={isVoiceActive ? "Mute Microphone" : "Enable Microphone"}
              >
                {isVoiceActive ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5 opacity-40" />}
              </button>
              <button onClick={() => setIsOpen(false)} className="p-2.5 rounded-xl bg-white/5 text-white/70 hover:bg-white/10 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 bg-stone-50/50">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[88%] p-5 rounded-2xl text-[14px] ${msg.role === 'user' ? 'bg-emerald-900 text-white rounded-tr-none shadow-md' : 'bg-white text-stone-800 border border-stone-100 rounded-tl-none font-serif italic shadow-sm'}`}>{msg.text}</div>
              </div>
            ))}
            {isVoiceActive && (
              <div className="flex justify-start">
                <div className="bg-emerald-50 border border-emerald-100 px-4 py-2 rounded-full flex items-center gap-2">
                  <div className="flex gap-1">
                    <span className="w-1 h-1 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-1 h-1 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-1 h-1 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                  <span className="text-[10px] text-emerald-800 font-bold uppercase tracking-wider">Jessica is listening...</span>
                </div>
              </div>
            )}
          </div>
          <div className="p-4 bg-white border-t border-stone-100 flex gap-3">
            <input 
              type="text" 
              value={input} 
              onChange={(e) => setInput(e.target.value)} 
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()} 
              placeholder="Type your question..." 
              className="flex-1 bg-stone-100/80 rounded-2xl px-6 py-3.5 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-900/10 transition-all" 
            />
            <button onClick={handleSendMessage} className="w-12 h-12 bg-emerald-900 text-white rounded-2xl flex items-center justify-center active:scale-95 transition-transform hover:bg-emerald-800 shadow-sm"><Send className="w-5 h-5" /></button>
          </div>
        </div>
      )}
    </>
  );
};

// --- Professional Crest Logo ---
const ProfessionalLogo = () => (
  <div className="flex flex-col items-center justify-center group cursor-pointer transition-all duration-700">
    <div className="relative w-14 h-14 mb-2">
      {/* 3s Continuous Loop Animation */}
      <div className="absolute inset-0 border-[0.5px] border-white/30 rotate-45 animate-slow-rotate-loop"></div>
      <div className="absolute inset-[3px] border border-white/50 flex items-center justify-center bg-stone-900/10 backdrop-blur-sm animate-pulse-scale-loop">
        <span className="font-serif text-white text-2xl font-bold italic drop-shadow-2xl">NM</span>
      </div>
      <div className="absolute -top-1 left-1/2 -translate-x-1/2 flex gap-[1px]">
        <div className="w-[1px] h-1.5 bg-white/40"></div>
      </div>
    </div>
    <div className="text-center">
      <h1 className="font-serif text-white text-3xl tracking-[0.2em] uppercase font-bold leading-none">Natasha Mae’s</h1>
      <p className="text-[20px] text-white/50 tracking-[0.4em] uppercase font-bold mt-1.5">Enterprise</p>
    </div>
  </div>
);

// --- Navigation ---
const Navbar = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isDarkSection, setIsDarkSection] = useState(true);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);

      // Detect if we're in a light or dark section
      const sections = [
        { id: 'venues', isDark: false },
        { id: 'virtual-tour', isDark: true },
        { id: 'designs', isDark: false },
        { id: 'dining', isDark: false },
        { id: 'pricing', isDark: false },
        { id: 'gallery', isDark: false },
      ];

      let currentIsDark = true;
      for (const section of sections) {
        const element = document.getElementById(section.id);
        if (element) {
          const rect = element.getBoundingClientRect();
          if (rect.top <= window.innerHeight / 2) {
            currentIsDark = section.isDark;
          }
        }
      }
      setIsDarkSection(currentIsDark);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const links = [
    { name: 'VENUES', href: '#venues' },
    { name: 'THEMED SET-UPS', href: '#designs' },
    { name: 'DIVINE DINING', href: '#dining' },
    { name: 'PRICING', href: '#pricing' },
    { name: 'GALLERY', href: '#gallery' },
  ];

  const textColor = isScrolled && !isDarkSection ? 'text-stone-900' : 'text-white';
  const socialColor = isScrolled && !isDarkSection ? 'text-stone-900/50 hover:text-stone-900' : 'text-white/50 hover:text-white';
  const logoColor = isScrolled && !isDarkSection ? 'text-stone-900' : 'text-white';
  const borderColor = isScrolled && !isDarkSection ? 'border-stone-900/10' : 'border-white/10';
  const navBg = isScrolled ? (isDarkSection ? 'bg-stone-950/98' : 'bg-white/95') : 'bg-transparent';

  return (
    <nav className={`fixed w-full z-50 transition-all duration-300 ${navBg} ${isScrolled ? 'pt-2 pb-6 shadow-2xl' : 'pt-6'}`}>
      <div className="max-w-[1400px] mx-auto px-8">
        <div className="flex justify-between items-center mb-2">
          <div className={`w-1/4 flex gap-6 ${socialColor}`}>
            <Instagram className="w-3.5 h-3.5 transition-colors cursor-pointer" />
            <Facebook className="w-3.5 h-3.5 transition-colors cursor-pointer" />
            <Linkedin className="w-3.5 h-3.5 transition-colors cursor-pointer" />
          </div>
          <div className={`w-2/4 ${logoColor} transition-colors`}>
            <ProfessionalLogo />
          </div>
          <div className="w-1/4"></div>
        </div>

        <div className={`flex justify-center gap-12 border-t ${borderColor} pt-2 flex-wrap transition-colors`}>
          {links.map((link) => (
            <a 
              key={link.name} 
              href={link.href} 
              className={`${textColor} text-[10px] uppercase tracking-[0.35em] font-bold hover:text-emerald-400 transition-all duration-300 relative group`}
            >
              {link.name}
              <span className="absolute -bottom-1 left-0 w-0 h-[1px] bg-emerald-400 transition-all duration-500 group-hover:w-full"></span>
            </a>
          ))}
        </div>
      </div>
    </nav>
  );
};

// --- Hero Section ---
const Hero = ({ openChat }: { openChat: () => void }) => {
  return (
    <section className="relative min-h-[115vh] flex flex-col items-center justify-start overflow-hidden bg-stone-950">
      <div className="absolute inset-0 z-0">
        <img 
          src="https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&q=80&w=2000" 
          className="w-full h-full object-cover opacity-45 animate-[ken-burns_30s_infinite_alternate]"
          alt="Luxury Estate" 
        />
        <div className="absolute inset-0 bg-gradient-to-b from-stone-950/70 via-transparent to-stone-950"></div>
      </div>
      
      {/* Grouped Hero Content: Just below the navbar with a small space */}
      <div className="relative z-10 text-center px-6 max-w-6xl pt-48 pb-20">
        <div className="space-y-2 mb-12 animate-fadeInUp">
           <span className="text-white text-base md:text-lg uppercase tracking-[0.6em] font-light opacity-90 block leading-none mt-8">The Premier Banquet Experience</span>
           <h2 className="text-5xl md:text-7xl text-white font-bold leading-[1.1] tracking-tighter">
             Three Iconic <br /><span className="font-serif italic text-white/80">Destinations</span>
           </h2>
           <p className="text-stone-300 text-lg md:text-xl max-w-3xl mx-auto font-light italic leading-relaxed opacity-80">
             "One Unforgettable Standard of Elegance Across the Delaware Valley."
           </p>
        </div>
        
        {/* Scaled-down Quick Venue Previews */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16 animate-fadeInUp max-w-5xl mx-auto scale-75 origin-top" style={{ animationDelay: '300ms' }}>
          {VENUES.map((venue) => (
            <a key={venue.id} href={`#${venue.id}`} className="group relative aspect-[4/5] overflow-hidden rounded-xl border border-white/10 shadow-2xl bg-stone-900 transition-all duration-700 hover:-translate-y-1">
              <img src={venue.image} className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-1000 group-hover:scale-110 opacity-70 group-hover:opacity-100" alt={venue.name} />
              <div className="absolute inset-0 bg-gradient-to-t from-stone-950 via-stone-950/20 to-transparent opacity-90 group-hover:opacity-40 transition-opacity"></div>
              <div className="absolute bottom-6 left-6 text-left">
                <span className="text-[9px] text-emerald-400 font-black uppercase tracking-[0.3em]">{venue.location}</span>
                <h4 className="text-white text-lg font-serif italic mt-1">{venue.name}</h4>
              </div>
            </a>
          ))}
        </div>
        
        {/* Scaled-down Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-8 animate-fadeInUp" style={{ animationDelay: '500ms' }}>
          <button onClick={openChat} className="w-full sm:w-auto bg-white text-stone-950 px-12 py-6 text-[11px] font-black uppercase tracking-[0.5em] hover:bg-emerald-900 hover:text-white transition-all shadow-4xl active:scale-95">
            TALK TO ASSISTANT
          </button>
          <a href="#virtual-tour" className="w-full sm:w-auto border border-white/20 text-white px-12 py-6 text-[11px] font-bold uppercase tracking-[0.5em] hover:bg-white hover:text-stone-950 transition-all flex items-center justify-center gap-4 group active:scale-95">
            VIRTUAL TOUR <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </a>
        </div>
      </div>
    </section>
  );
};

// --- Virtual Tour Section ---
const VirtualTour = () => (
  <section id="virtual-tour" className="py-56 bg-stone-950 relative overflow-hidden">
    <div className="absolute inset-0 opacity-10">
      <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]"></div>
    </div>
    <div className="max-w-7xl mx-auto px-8 relative z-10">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
        <div>
          <span className="text-emerald-500 text-[11px] uppercase tracking-[0.6em] font-black block mb-6">Digital Experience</span>
          <h2 className="text-5xl md:text-7xl font-bold text-white tracking-tight leading-tight mb-8">Walk Through <br /><span className="font-serif italic text-white/60">Grandeur</span></h2>
          <p className="text-stone-400 text-xl leading-relaxed mb-12 max-w-lg">
            Immerse yourself in our historic ballrooms and modern event spaces from the comfort of your home. Every detail is curated for your perfection.
          </p>
          <div className="space-y-6">
            <div className="flex items-center gap-6 group cursor-pointer border border-white/5 p-5 rounded-2xl hover:bg-white/5 transition-all">
              <div className="w-14 h-14 rounded-full border border-white/10 flex items-center justify-center group-hover:bg-white group-hover:text-stone-950 transition-all">
                <Play className="w-6 h-6 ml-1" />
              </div>
              <div>
                <h4 className="text-white font-bold uppercase tracking-widest text-sm">Vault Ballroom Cinematic Tour</h4>
                <p className="text-stone-500 text-xs mt-1">4K resolution • 3:15 Minutes</p>
              </div>
            </div>
            <div className="flex items-center gap-6 group cursor-pointer border border-white/5 p-5 rounded-2xl hover:bg-white/5 transition-all">
              <div className="w-14 h-14 rounded-full border border-white/10 flex items-center justify-center group-hover:bg-white group-hover:text-stone-950 transition-all">
                <Maximize2 className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-white font-bold uppercase tracking-widest text-sm">360° Interactive Experience</h4>
                <p className="text-stone-500 text-xs mt-1">Explore the Liberty Palace Patio</p>
              </div>
            </div>
          </div>
        </div>
        <div className="relative group">
          <div className="aspect-video bg-stone-900 rounded-[3rem] overflow-hidden shadow-6xl relative border border-white/10">
            <img src="https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&q=80&w=1200" className="w-full h-full object-cover opacity-60 group-hover:scale-105 transition-transform duration-1000" alt="Virtual Tour Cover" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-24 h-24 bg-white/5 backdrop-blur-xl rounded-full flex items-center justify-center animate-pulse border border-white/20">
                <Play className="w-10 h-10 text-white" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
);

// --- Themed Set-ups Section ---
const Designs = () => (
  <section id="designs" className="py-56 bg-white relative overflow-hidden">
    <div className="max-w-[1500px] mx-auto px-8">
      <div className="text-center mb-28 max-w-4xl mx-auto">
        <span className="text-emerald-800 text-[11px] uppercase tracking-[0.6em] font-black block mb-6">Heavenly Designs</span>
        <h2 className="text-6xl md:text-8xl font-bold text-stone-900 tracking-tighter leading-none mb-10">Where Themes <br /><span className="font-serif italic text-stone-800/40">Come Alive</span></h2>
        <p className="text-stone-500 text-xl font-light leading-relaxed italic max-w-2xl mx-auto">
          "From Gatsby Glamour to Custom Marvel Fantasies, we don't just decorate—we transport your guests to another world."
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
        {[
          { icon: <Palette className="w-8 h-8" />, title: "Themed Masterpieces", text: "Spectacular in-house floral and decor packages—from Harlem Nights to custom children's themes." },
          { icon: <Sparkles className="w-8 h-8" />, title: "Floral Ethereal", text: "Heavenly floral arrangements that create a fragrant and visually stunning atmosphere." },
          { icon: <Clock className="w-8 h-8" />, title: "Seamless Logistics", text: "Complete setup and breakdown managed by your personal event manager." }
        ].map((item, idx) => (
          <div key={idx} className="p-10 bg-stone-50 rounded-[2.5rem] border border-stone-100 group hover:bg-stone-900 transition-all duration-700">
            <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center text-stone-900 mb-8 group-hover:bg-emerald-800 group-hover:text-white transition-all shadow-sm">
              {item.icon}
            </div>
            <h4 className="text-2xl font-bold text-stone-900 mb-4 group-hover:text-white">{item.title}</h4>
            <p className="text-stone-500 group-hover:text-stone-400 font-medium leading-relaxed">{item.text}</p>
          </div>
        ))}
      </div>
    </div>
  </section>
);

// --- Divine Dining Section ---
const Dining = () => (
  <section id="dining" className="py-56 bg-stone-50">
    <div className="max-w-[1400px] mx-auto px-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
        <div className="relative">
          <div className="aspect-[4/5] bg-stone-200 rounded-[3.5rem] overflow-hidden shadow-6xl">
            <img src="https://images.unsplash.com/photo-1555244162-803834f70033?auto=format&fit=crop&q=80&w=1200" className="w-full h-full object-cover" alt="Divine Dining" />
          </div>
          <div className="absolute -bottom-12 -right-12 bg-white p-10 rounded-[2rem] shadow-4xl max-w-sm hidden md:block border border-stone-100">
             <UtensilsCrossed className="w-10 h-10 text-emerald-800 mb-6" />
             <h4 className="text-2xl font-serif italic mb-4">Chef's Signature</h4>
             <p className="text-stone-500 text-sm leading-relaxed">Artisanal menus featuring seasonal local produce and specialized dietary considerations (Vegan & Gluten-Free).</p>
          </div>
        </div>
        <div className="space-y-10">
          <span className="text-emerald-800 text-[11px] uppercase tracking-[0.6em] font-black block">The Culinary Standard</span>
          <h2 className="text-6xl md:text-7xl font-bold text-stone-900 tracking-tight leading-tight">Divine <br /><span className="font-serif italic text-stone-400">Dining</span></h2>
          <p className="text-stone-600 text-xl font-light leading-relaxed">
            In-house catering that maintains the highest standards for every palate. Our chefs specialize in gourmet collections tailored to your event's theme.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-8 pt-6">
            <div className="flex gap-4">
               <CheckCircle2 className="w-6 h-6 text-emerald-800 shrink-0" />
               <div>
                  <h5 className="font-bold text-sm uppercase tracking-widest text-stone-900">Organic Sourcing</h5>
                  <p className="text-stone-500 text-xs mt-1">Farm-to-table excellence.</p>
               </div>
            </div>
            <div className="flex gap-4">
               <CheckCircle2 className="w-6 h-6 text-emerald-800 shrink-0" />
               <div>
                  <h5 className="font-bold text-sm uppercase tracking-widest text-stone-900">Vegan Expertise</h5>
                  <p className="text-stone-500 text-xs mt-1">Delicious plant-based luxury.</p>
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
);

// --- Pricing Section ---
const Pricing = () => (
  <section id="pricing" className="py-56 bg-white">
    <div className="max-w-[1250px] mx-auto px-8">
      <div className="text-center mb-36">
        <span className="text-emerald-800 text-[11px] uppercase tracking-[0.6em] font-black block mb-6">Transparent Investing</span>
        <h2 className="text-6xl md:text-8xl font-bold text-stone-900 tracking-tighter leading-tight">Investment Tiers</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {[
          { title: "Intimate Urban", price: "1,000", venue: "Frankford Facility", capacity: "110", perks: ["4 Hour Access", "Basic Decor", "Near SEPTA Station"] },
          { title: "Elite Session", price: "3,000", venue: "Liberty Palace", capacity: "210", perks: ["Outdoor Patio", "Parking Concierge", "Natural Light", "Strategic Location"] },
          { title: "Royal Ballroom", price: "3,795", venue: "The Vault Ballroom", capacity: "250", perks: ["Historic Architecture", "5 AM License", "Cobblestone Garden", "VIP Concierge"] }
        ].map((pkg, i) => (
          <div key={i} className={`p-12 rounded-[3rem] border ${i === 2 ? 'bg-stone-950 text-white border-transparent shadow-6xl scale-105' : 'bg-white text-stone-900 border-stone-100 shadow-xl'} transition-all hover:-translate-y-2 duration-500`}>
            <span className={`text-[10px] font-black uppercase tracking-widest block mb-6 ${i === 2 ? 'text-emerald-400' : 'text-emerald-800'}`}>{pkg.venue}</span>
            <h4 className="text-3xl font-serif italic mb-2">{pkg.title}</h4>
            <div className="flex items-baseline gap-2 mb-10">
              <span className="text-lg opacity-40 font-bold">$</span>
              <span className="text-4xl font-black tracking-tighter">{pkg.price}</span>
              <span className="text-xs font-bold tracking-widest opacity-40 uppercase ml-2">/ Minimum</span>
            </div>
            <ul className="space-y-5 mb-14 pt-8 border-t border-stone-100/10">
              {pkg.perks.map((p, idx) => (
                <li key={idx} className="flex items-center gap-4 text-sm font-medium">
                  <CheckCircle2 className={`w-5 h-5 ${i === 2 ? 'text-emerald-400' : 'text-emerald-800'}`} /> {p}
                </li>
              ))}
              <li className="flex items-center gap-4 text-sm font-medium opacity-60">
                <Maximize2 className="w-5 h-5" /> Up to {pkg.capacity} Capacity
              </li>
            </ul>
            <button className={`w-full py-5 rounded-2xl text-[10px] font-black uppercase tracking-[0.4em] transition-all ${i === 2 ? 'bg-emerald-800 text-white hover:bg-emerald-700' : 'bg-stone-900 text-white hover:bg-stone-800'}`}>
              INQUIRE NOW
            </button>
          </div>
        ))}
      </div>
    </div>
  </section>
);

// --- Gallery Section ---
const Gallery = () => (
  <section id="gallery" className="py-56 bg-stone-50">
    <div className="max-w-[1600px] mx-auto px-8">
      <div className="flex flex-col md:flex-row justify-between items-end mb-28 gap-10">
        <div className="max-w-2xl">
          <span className="text-emerald-800 text-[11px] uppercase tracking-[0.6em] font-black block mb-6">Captured Moments</span>
          <h2 className="text-6xl md:text-7xl font-bold text-stone-900 tracking-tighter leading-tight">Visual <br /><span className="font-serif italic text-stone-400">Portfolio</span></h2>
        </div>
        <button className="bg-stone-900 text-white px-12 py-7 rounded-2xl text-[10px] font-black uppercase tracking-[0.4em] hover:bg-emerald-950 transition-all">OPEN FULL ALBUM</button>
      </div>
      <div className="columns-1 md:columns-2 lg:columns-3 gap-8 space-y-8">
        {[
          'https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&q=80&w=800',
          'https://images.unsplash.com/photo-1464366400600-7168b8af9bc3?auto=format&fit=crop&q=80&w=800',
          'https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&q=80&w=800',
          'https://images.unsplash.com/photo-1523438885200-e635ba2c371e?auto=format&fit=crop&q=80&w=800',
          'https://images.unsplash.com/photo-1502633596451-88d44716b2f4?auto=format&fit=crop&q=80&w=800',
          'https://images.unsplash.com/photo-1555244162-803834f70033?auto=format&fit=crop&q=80&w=1200',
        ].map((src, i) => (
          <div key={i} className="group relative overflow-hidden rounded-[2.5rem] bg-stone-200 cursor-pointer shadow-xl transition-all hover:scale-[1.02] duration-500">
            <img src={src} className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-110" alt="Gallery item" />
            <div className="absolute inset-0 bg-stone-950/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <div className="w-16 h-16 bg-white/10 backdrop-blur-md rounded-full flex items-center justify-center border border-white/20">
                <ImageIcon className="text-white w-6 h-6" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  </section>
);

// --- Venue Details Section ---
const VenueShowcase = () => (
  <section id="venues" className="py-56 bg-stone-50 border-b border-stone-200">
    <div className="max-w-[1500px] mx-auto px-8">
      <div className="text-center mb-36 max-w-4xl mx-auto">
        <span className="text-emerald-800 text-[11px] uppercase tracking-[0.6em] font-black block mb-6">Three Signature Locations</span>
        <h2 className="text-5xl md:text-8xl font-bold text-stone-900 tracking-tight leading-tight">The Collection</h2>
        <div className="w-24 h-[1px] bg-stone-900/10 mx-auto mt-12"></div>
      </div>
      <div className="grid grid-cols-1 gap-64">
        {VENUES.map((venue, idx) => (
          <div key={venue.id} id={venue.id} className={`flex flex-col lg:flex-row gap-20 items-center scroll-mt-32 ${idx % 2 !== 0 ? 'lg:flex-row-reverse' : ''}`}>
            <div className="w-full lg:w-[60%] group relative overflow-hidden rounded-[3.5rem] shadow-6xl aspect-[16/9] bg-stone-200">
              <img src={venue.image} alt={venue.name} className="w-full h-full object-cover transition-transform duration-[4s] group-hover:scale-105" />
              <div className="absolute inset-0 bg-stone-950/5 group-hover:bg-transparent transition-all"></div>
            </div>
            <div className="w-full lg:w-[40%] space-y-10">
              <div className="space-y-6">
                <span className="text-emerald-800 text-[11px] uppercase font-black tracking-[0.4em] block">{venue.location}</span>
                <h3 className="text-5xl md:text-6xl font-bold text-stone-900 leading-tight tracking-tighter">{venue.name}</h3>
                <p className="text-stone-500 text-xl italic font-light leading-relaxed">"{venue.details}"</p>
                <div className="flex flex-wrap gap-4 pt-4">
                  <span className="bg-stone-100 px-5 py-3 rounded-full text-[10px] font-bold text-stone-600 uppercase tracking-widest">{venue.vibe}</span>
                  <span className="bg-stone-100 px-5 py-3 rounded-full text-[10px] font-bold text-stone-600 uppercase tracking-widest">{venue.capacity}</span>
                </div>
              </div>
              <button className="bg-stone-950 text-white px-10 py-7 text-[11px] uppercase tracking-[0.45em] font-black hover:bg-emerald-900 transition-all shadow-5xl flex items-center justify-between w-full active:scale-95">
                REQUEST VIP ACCESS <ArrowUpRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  </section>
);

const App: React.FC = () => {
  const [isChatOpen, setIsChatOpen] = useState(false);
  
  return (
    <div className="bg-stone-950 selection:bg-emerald-900 selection:text-white scroll-smooth min-h-screen">
      <Navbar />
      <Hero openChat={() => setIsChatOpen(true)} />
      
      <main className="relative z-10">
        <VenueShowcase />
        <VirtualTour />
        <Designs />
        <Dining />
        <Pricing />
        <Gallery />
        
        {/* Call to Action Section */}
        <section className="py-56 bg-white relative overflow-hidden">
          <div className="max-w-5xl mx-auto px-6 text-center relative z-10">
            <h3 className="text-5xl md:text-[7rem] font-serif mb-20 italic text-stone-900 leading-[0.9] tracking-tighter">Your grand milestone begins with a VIP Tour.</h3>
            <div className="flex flex-col sm:flex-row justify-center gap-8">
              <button onClick={() => setIsChatOpen(true)} className="bg-stone-950 text-white px-24 py-8 uppercase text-[12px] font-black tracking-[0.5em] shadow-6xl hover:bg-emerald-950 transition-all active:scale-95">TALK TO ASSISTANT</button>
              <a href="tel:2676550230" className="bg-stone-100 text-stone-900 px-24 py-8 uppercase text-[12px] font-black tracking-[0.5em] hover:bg-stone-200 transition-all active:scale-95 flex items-center justify-center gap-4">
                <Phone className="w-4 h-4" /> 267-655-0230
              </a>
            </div>
          </div>
        </section>
      </main>
      
      {/* Footer */}
      <footer className="bg-stone-950 py-44 text-center px-8 border-t border-white/5">
        <div className="max-w-6xl mx-auto space-y-28">
          <ProfessionalLogo />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-16 text-left">
            <div className="space-y-6">
              <h5 className="text-white text-[10px] font-black uppercase tracking-[0.4em] border-b border-white/10 pb-4">Destinations</h5>
              <ul className="space-y-4 text-white/40 text-[10px] font-bold uppercase tracking-[0.3em]">
                <li><a href="#vault" className="hover:text-emerald-400 transition-colors">The Vault Ballroom</a></li>
                <li><a href="#liberty" className="hover:text-emerald-400 transition-colors">Mae's Liberty Palace</a></li>
                <li><a href="#banquet" className="hover:text-emerald-400 transition-colors">Frankford Facility</a></li>
              </ul>
            </div>
            <div className="space-y-6">
              <h5 className="text-white text-[10px] font-black uppercase tracking-[0.4em] border-b border-white/10 pb-4">Exclusives</h5>
              <ul className="space-y-4 text-white/40 text-[10px] font-bold uppercase tracking-[0.3em]">
                <li><a href="#designs" className="hover:text-emerald-400 transition-colors">Heavenly Designs</a></li>
                <li><a href="#dining" className="hover:text-emerald-400 transition-colors">Divine Dining</a></li>
                <li><a href="#pricing" className="hover:text-emerald-400 transition-colors">Pricing Framework</a></li>
              </ul>
            </div>
            <div className="space-y-6">
              <h5 className="text-white text-[10px] font-black uppercase tracking-[0.4em] border-b border-white/10 pb-4">Experience</h5>
              <ul className="space-y-4 text-white/40 text-[10px] font-bold uppercase tracking-[0.3em]">
                <li><a href="#virtual-tour" className="hover:text-emerald-400 transition-colors">Virtual Tours</a></li>
                <li><a href="#gallery" className="hover:text-emerald-400 transition-colors">Photo Gallery</a></li>
                <li><a href="#" className="hover:text-emerald-400 transition-colors">Client Reviews</a></li>
              </ul>
            </div>
            <div className="space-y-6">
              <h5 className="text-white text-[10px] font-black uppercase tracking-[0.4em] border-b border-white/10 pb-4">Connect</h5>
              <ul className="space-y-4 text-white/40 text-[10px] font-bold uppercase tracking-[0.3em]">
                <li><a href="#" className="hover:text-emerald-400 transition-colors">Instagram</a></li>
                <li><a href="#" className="hover:text-emerald-400 transition-colors">Facebook</a></li>
                <li><a href="#" className="hover:text-emerald-400 transition-colors">LinkedIn</a></li>
              </ul>
            </div>
          </div>
          <div className="pt-20 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-8 text-white/20 uppercase tracking-[0.8em] text-[10px] font-bold">
            <p>© {new Date().getFullYear()} Natasha Mae’s Enterprise</p>
            <p className="tracking-widest opacity-60">Premier Venue Management Portfolio</p>
          </div>
        </div>
      </footer>
      
      <ChatBot isOpen={isChatOpen} setIsOpen={setIsChatOpen} />
      
      <style>{`
        @keyframes ken-burns { 0% { transform: scale(1); } 100% { transform: scale(1.1); } }
        @keyframes fadeInUp { from { transform: translateY(60px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        
        /* Continuous Logo Animation Loops - Exactly 3s */
        @keyframes slowRotateLoop { 
          0% { transform: rotate(45deg); } 
          100% { transform: rotate(405deg); } 
        }
        @keyframes pulseScaleLoop { 
          0%, 100% { transform: scale(1); } 
          50% { transform: scale(1.08); } 
        }
        
        .animate-fadeInUp { animation: fadeInUp 1.8s cubic-bezier(0.19, 1, 0.22, 1) both; }
        .animate-fadeIn { animation: fadeIn 0.8s ease-out both; }
        .animate-slow-rotate-loop { animation: slowRotateLoop 3s linear infinite; }
        .animate-pulse-scale-loop { animation: pulseScaleLoop 3s ease-in-out infinite; }

        html { scroll-behavior: smooth; }
        body { -webkit-font-smoothing: antialiased; background-color: #0c0a09; color: white; overflow-x: hidden; }
        
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #0c0a09; }
        ::-webkit-scrollbar-thumb { background: #1c1917; border-radius: 4px; border: 2px solid #0c0a09; }
        ::-webkit-scrollbar-thumb:hover { background: #262626; }
      `}</style>
    </div>
  );
};

export default App;
