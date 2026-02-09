import React from 'react';
import { ChevronRight } from 'lucide-react';
import { VENUES } from '../constants';

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

const Designs = () => {
  return (
    <>
      <section className="relative min-h-[115vh] flex flex-col items-center justify-start overflow-hidden bg-stone-950">
        <div className="absolute inset-0 z-0">
          <img 
            src="/images/hero/header-background.jpg" 
            className="w-full h-full object-cover opacity-45 animate-[ken-burns_30s_infinite_alternate]"
            alt="Luxury Estate" 
          />
          <div className="absolute inset-0 bg-gradient-to-b from-stone-950/70 via-transparent to-stone-950"></div>
        </div>
        
        <div className="relative z-10 text-center px-6 max-w-6xl pt-32 pb-20">
          <div className="space-y-2 mb-12 animate-fadeInUp">
            <span className="text-white text-base md:text-lg uppercase tracking-[0.6em] font-light opacity-90 block leading-none mt-8">Heavenly Designs</span>
            <h2 className="text-5xl md:text-7xl text-white font-bold leading-[1.1] tracking-tighter">
              Three Iconic <br /><span className="font-serif italic text-white/80">Destinations</span>
            </h2>
            <p className="text-stone-300 text-lg md:text-xl max-w-3xl mx-auto font-light italic leading-relaxed opacity-80">
              "One Unforgettable Standard of Elegance Across the Delaware Valley."
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16 animate-fadeInUp max-w-5xl mx-auto scale-75 origin-top" style={{ animationDelay: '300ms' }}>
            {VENUES.map((venue) => (
              <a key={venue.id} href={`/venues#${venue.id}`} className="group relative aspect-[4/5] overflow-hidden rounded-xl border border-white/10 shadow-2xl bg-stone-900 transition-all duration-700 hover:-translate-y-1">
                <img src={venue.image} className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-1000 group-hover:scale-110 opacity-70 group-hover:opacity-100" alt={venue.name} />
                <div className="absolute inset-0 bg-gradient-to-t from-stone-950 via-stone-950/20 to-transparent opacity-90 group-hover:opacity-40 transition-opacity"></div>
                <div className="absolute bottom-6 left-6 text-left">
                  <span className="text-[9px] text-emerald-400 font-black uppercase tracking-[0.3em]">{venue.location}</span>
                  <h4 className="text-white text-lg font-serif italic mt-1">{venue.name}</h4>
                </div>
              </a>
            ))}
          </div>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-8 animate-fadeInUp" style={{ animationDelay: '500ms' }}>
            <a href="/venues" className="bg-white text-stone-950 px-16 py-6 uppercase text-[11px] font-black tracking-[0.5em] shadow-6xl hover:bg-emerald-400 transition-all active:scale-95 flex items-center gap-3">EXPLORE VENUES <ChevronRight className="w-4 h-4" /></a>
            <a href="/contact" className="text-white px-16 py-6 uppercase text-[11px] font-black tracking-[0.5em] border-2 border-white hover:bg-white hover:text-stone-950 transition-all active:scale-95">SCHEDULE CONSULTATION</a>
          </div>
        </div>
      </section>
    </>
  );
};

export default Designs;
