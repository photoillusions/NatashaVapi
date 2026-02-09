import React from 'react';

const Pricing = () => (
  <section className="relative min-h-[115vh] flex flex-col items-center justify-start overflow-hidden bg-stone-950">
    <div className="absolute inset-0 z-0">
      <img src="/images/hero/header-background.jpg" className="w-full h-full object-cover opacity-45 animate-[ken-burns_30s_infinite_alternate]" alt="Luxury Estate" />
      <div className="absolute inset-0 bg-gradient-to-b from-stone-950/70 via-transparent to-stone-950"></div>
    </div>
    <div className="relative z-10 text-center px-6 max-w-6xl pt-32 pb-20">
      <h2 className="text-5xl md:text-7xl text-white font-bold leading-[1.1] tracking-tighter">Contracts / Pricing</h2>
      <p className="text-stone-300 text-lg md:text-xl max-w-3xl mx-auto font-light italic leading-relaxed opacity-80 mt-4">This page will provide pricing and contract information. (Content coming soon)</p>
    </div>
  </section>
);

export default Pricing;
