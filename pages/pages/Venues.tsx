import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { VENUES } from '../constants';
import PageHeader from '../components/PageHeader';

const Venues = () => {
  return (
    <>
      <PageHeader 
        subtitle="Premier Venues"
        title="Our Signature Locations"
        description="Discover the perfect venue for your unforgettable celebration."
      />

      {/* Venues Content */}
      <section className="py-56 bg-stone-50 border-b border-stone-200">
        <div className="max-w-[1500px] mx-auto px-8">
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
    </>
  );
};

export default Venues;
