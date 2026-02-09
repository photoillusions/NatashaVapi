import React from 'react';
import { ArrowUpRight, MapPin, Users, DollarSign } from 'lucide-react';
import { VENUES } from '../constants';
import PageHeader from '../components/PageHeader';

const Venues = () => {
  return (
    <>
      <PageHeader 
        subtitle="Multi-Asset Portfolio"
        title="Natasha Mae's Enterprises: A Venue for Every Vision"
        description="Four distinct locations, four unique personalities—each designed to deliver the perfect event experience at every scale and budget."
      />

      {/* Portfolio Overview */}
      <section className="py-40 bg-stone-50 border-b border-stone-200">
        <div className="max-w-5xl mx-auto px-8">
          <div className="space-y-10 text-center mb-28">
            <h3 className="text-4xl md:text-5xl font-bold text-stone-900 leading-tight">The Tiered Asset Model</h3>
            <p className="text-lg text-stone-600 italic max-w-3xl mx-auto font-light">
              By offering a carefully curated portfolio of venues, we ensure that your event—whether a micro-wedding or a grand corporate gala—finds its perfect home in a space designed for its specific scale, character, and vision.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-white p-8 rounded-2xl border border-stone-200 shadow-lg">
              <h4 className="text-xl font-bold text-stone-900 mb-4">Why Our Portfolio Matters</h4>
              <ul className="space-y-3 text-stone-600 text-sm">
                <li className="flex gap-3">
                  <span className="text-emerald-800 font-bold">•</span>
                  <span>Every guest deserves a venue that matches their event's scale</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-emerald-800 font-bold">•</span>
                  <span>No "cavernous hall" experiences for intimate celebrations</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-emerald-800 font-bold">•</span>
                  <span>Personal Event Manager ensures consistent excellence across all locations</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-emerald-800 font-bold">•</span>
                  <span>Unified "Mrs. Natasha" touch with distinct architectural personalities</span>
                </li>
              </ul>
            </div>
            
            <div className="bg-white p-8 rounded-2xl border border-stone-200 shadow-lg">
              <h4 className="text-xl font-bold text-stone-900 mb-4">Our Commitment</h4>
              <p className="text-stone-600 text-sm mb-6 leading-relaxed">
                Founded in 2000 as a niche floristry provider, we have evolved into a premier hospitality leader in the Delaware Valley. Our vertical integration—controlling venues, design, and catering—ensures that every detail reflects our 24-year legacy of excellence.
              </p>
              <p className="text-stone-600 text-sm leading-relaxed italic">
                Every celebration is guided by a dedicated Personal Event Manager, ensuring your vision is realized with the professionalism, heart, and attention to detail that has made us a community cornerstone.
              </p>
            </div>
          </div>
        </div>
      </section>

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
                    <p className="text-stone-600 text-lg italic font-light leading-relaxed">"{venue.details}"</p>
                    
                    <div className="space-y-4 pt-6">
                      <div>
                        <h4 className="text-[11px] font-black text-stone-900 uppercase tracking-[0.3em] mb-3">Key Features</h4>
                        <ul className="space-y-2">
                          {venue.features.map((feature, i) => (
                            <li key={i} className="text-sm text-stone-600 flex gap-3">
                              <span className="text-emerald-800 font-bold mt-1">✓</span>
                              <span>{feature}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 pt-6 border-t border-stone-200">
                      <div>
                        <span className="text-[9px] font-black uppercase text-stone-500 tracking-[0.2em] block mb-2">VIBE</span>
                        <p className="text-sm font-semibold text-stone-900">{venue.vibe}</p>
                      </div>
                      <div>
                        <span className="text-[9px] font-black uppercase text-stone-500 tracking-[0.2em] block mb-2">CAPACITY</span>
                        <p className="text-sm font-semibold text-stone-900">{venue.capacity}</p>
                      </div>
                      <div>
                        <span className="text-[9px] font-black uppercase text-stone-500 tracking-[0.2em] block mb-2">STARTING</span>
                        <p className="text-sm font-semibold text-stone-900">{venue.pricing}</p>
                      </div>
                    </div>
                  </div>
                  <button className="bg-stone-950 text-white px-10 py-7 text-[11px] uppercase tracking-[0.45em] font-black hover:bg-emerald-900 transition-all shadow-5xl flex items-center justify-between w-full active:scale-95">
                    SCHEDULE TOUR <ArrowUpRight className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Vertical Services Section */}
      <section className="py-56 bg-white border-b border-stone-200">
        <div className="max-w-6xl mx-auto px-8">
          <div className="text-center mb-28 max-w-4xl mx-auto">
            <span className="text-emerald-800 text-[11px] uppercase tracking-[0.6em] font-black block mb-6">Supporting Services</span>
            <h2 className="text-5xl md:text-6xl font-bold text-stone-900 tracking-tighter leading-none mb-8">Vertical Integration Excellence</h2>
            <p className="text-stone-600 text-lg italic font-light max-w-2xl mx-auto">Our integrated service model ensures seamless execution and cost-effective quality control across every aspect of your celebration.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            <div className="space-y-6 p-10 rounded-2xl bg-stone-50 border border-stone-200">
              <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                <span className="text-emerald-800 text-2xl font-bold">✦</span>
              </div>
              <h3 className="text-2xl font-bold text-stone-900">Natasha's Heavenly Designs</h3>
              <p className="text-stone-600 leading-relaxed">Spectacular in-house floral and decor packages—from Harlem Nights/Gatsby elegance to custom children's themes. Our creative backbone ensures consistent excellence and total quality control.</p>
            </div>
            
            <div className="space-y-6 p-10 rounded-2xl bg-stone-50 border border-stone-200">
              <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                <span className="text-emerald-800 text-2xl font-bold">✦</span>
              </div>
              <h3 className="text-2xl font-bold text-stone-900">Divine Dining</h3>
              <p className="text-stone-600 leading-relaxed">In-house catering with extensive menus including vegan, vegetarian, and gluten-free options. Experience world-class culinary service tailored to your celebration's timeline and vision.</p>
            </div>
            
            <div className="space-y-6 p-10 rounded-2xl bg-stone-50 border border-stone-200">
              <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                <span className="text-emerald-800 text-2xl font-bold">✦</span>
              </div>
              <h3 className="text-2xl font-bold text-stone-900">Personal Event Management</h3>
              <p className="text-stone-600 leading-relaxed">Every celebration is guided by a dedicated Personal Event Manager who ensures your vision is realized with professionalism, heart, and meticulous attention to detail.</p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
};

export default Venues;
