import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Instagram, Facebook, Linkedin } from 'lucide-react';
import Home from './pages/Home';
import Venues from './pages/Venues';
import Gallery from './pages/Gallery';
import Designs from './pages/Designs';
import ThemedSetups from './pages/ThemedSetups';
import DivineDining from './pages/DivineDining';
import Pricing from './pages/Pricing';
import Contact from './pages/Contact';

// --- Navigation ---
const ProfessionalLogo = () => (
  <div className="flex flex-col items-center justify-center select-none">
    <div className="relative">
      <div className="absolute -top-1 left-1/2 -translate-x-1/2 flex gap-[1px]">
        <div className="w-[1px] h-1.5 bg-white/40"></div>
      </div>
    </div>
    <div className="text-center">
      <h1 className="font-serif text-white text-3xl tracking-[0.2em] uppercase font-bold leading-none">Natasha Mae's</h1>
      <p className="text-[20px] text-white/50 tracking-[0.4em] uppercase font-bold mt-1.5">Enterprise</p>
    </div>
  </div>
);

const Navbar = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isDarkSection, setIsDarkSection] = useState(true);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
      setIsDarkSection(true); // Default to dark for page navigation
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const links = [
    { name: 'HOME', href: '/' },
    { name: 'VENUES', href: '/venues' },
    { name: 'THEMED SET-UPS', href: '/#designs' },
    { name: 'DIVINE DINING', href: '/#dining' },
    { name: 'PRICING', href: '/#pricing' },
    { name: 'GALLERY', href: '/gallery' },
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
            <a href="/">
              <ProfessionalLogo />
            </a>
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

// --- Footer ---
const Footer = () => (
  <footer className="bg-stone-950 py-44 text-center px-8 border-t border-white/5">
    <div className="max-w-6xl mx-auto space-y-28">
      <ProfessionalLogo />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-16 text-left">
        <div className="space-y-6">
          <h5 className="text-white text-[10px] font-black uppercase tracking-[0.4em] border-b border-white/10 pb-4">Destinations</h5>
          <ul className="space-y-4 text-white/40 text-[10px] font-bold uppercase tracking-[0.3em]">
            <li><a href="/venues#vault" className="hover:text-emerald-400 transition-colors">The Vault Ballroom</a></li>
            <li><a href="/venues#liberty" className="hover:text-emerald-400 transition-colors">Mae's Liberty Palace</a></li>
            <li><a href="/venues#banquet" className="hover:text-emerald-400 transition-colors">Frankford Facility</a></li>
          </ul>
        </div>
        <div className="space-y-6">
          <h5 className="text-white text-[10px] font-black uppercase tracking-[0.4em] border-b border-white/10 pb-4">Exclusives</h5>
          <ul className="space-y-4 text-white/40 text-[10px] font-bold uppercase tracking-[0.3em]">
            <li><a href="/#designs" className="hover:text-emerald-400 transition-colors">Heavenly Designs</a></li>
            <li><a href="/#dining" className="hover:text-emerald-400 transition-colors">Divine Dining</a></li>
            <li><a href="/#pricing" className="hover:text-emerald-400 transition-colors">Pricing Framework</a></li>
          </ul>
        </div>
        <div className="space-y-6">
          <h5 className="text-white text-[10px] font-black uppercase tracking-[0.4em] border-b border-white/10 pb-4">Experience</h5>
          <ul className="space-y-4 text-white/40 text-[10px] font-bold uppercase tracking-[0.3em]">
            <li><a href="/#virtual-tour" className="hover:text-emerald-400 transition-colors">Virtual Tours</a></li>
            <li><a href="/gallery" className="hover:text-emerald-400 transition-colors">Photo Gallery</a></li>
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
        <p>© {new Date().getFullYear()} Natasha Mae's Enterprise</p>
        <p className="tracking-widest opacity-60">Premier Venue Management Portfolio</p>
      </div>
    </div>
  </footer>
);

const App: React.FC = () => {
  return (
    <Router>
      <div className="bg-stone-950 selection:bg-emerald-900 selection:text-white scroll-smooth min-h-screen">
        <Navbar />
        
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/designs" element={<Designs />} />
          <Route path="/venues" element={<Venues />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/themed-setups" element={<ThemedSetups />} />
          <Route path="/divine-dining" element={<DivineDining />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/contact" element={<Contact />} />
        </Routes>
        
        <Footer />
      </div>

      <style>{`
        @keyframes ken-burns { 0% { transform: scale(1); } 100% { transform: scale(1.1); } }
        @keyframes fadeInUp { from { transform: translateY(60px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        
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
    </Router>
  );
};

export default App;
