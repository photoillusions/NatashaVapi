import React, { useState } from 'react';
import { ChevronRight, Image as ImageIcon } from 'lucide-react';
import { VENUES } from '../constants';

const galleryImages = [
  'https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&q=80&w=800',
  'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&q=80&w=800',
  'https://images.unsplash.com/photo-1519224052708-081b537129dd?auto=format&fit=crop&q=80&w=800',
  'https://images.unsplash.com/photo-1527529482837-4698179dc6ce?auto=format&fit=crop&q=80&w=800',
  'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&q=80&w=800',
  'https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&q=80&w=800',
];

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

const Home = () => {
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
            <span className="text-white text-base md:text-lg uppercase tracking-[0.6em] font-light opacity-90 block leading-none mt-8">The Premier Banquet Experience</span>
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

      {/* Gallery Section */}
      <section className="py-56 bg-stone-50">
        <div className="max-w-[1600px] mx-auto px-8">
          <div className="text-center mb-28 max-w-4xl mx-auto">
            <span className="text-emerald-800 text-[11px] uppercase tracking-[0.6em] font-black block mb-6">Visual Showcase</span>
            <h2 className="text-5xl md:text-7xl font-bold text-stone-900 tracking-tighter leading-none mb-10">Event Gallery</h2>
            <p className="text-stone-500 text-lg italic max-w-2xl mx-auto">Explore our collection of stunning celebrations and elegant events hosted at our premier venues.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {galleryImages.map((src, i) => (
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
    </>
  );
};

export default Home;
