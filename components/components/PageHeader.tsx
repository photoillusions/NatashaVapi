import React from 'react';

interface PageHeaderProps {
  subtitle: string;
  title: string;
  description: string;
  imageUrl?: string;
}

const PageHeader: React.FC<PageHeaderProps> = ({ 
  subtitle, 
  title, 
  description,
  imageUrl = '/images/hero/header-background.jpg'
}) => {
  return (
    <section className="relative min-h-[70vh] flex flex-col items-center justify-center overflow-hidden bg-stone-950 pt-32">
      <div className="absolute inset-0 z-0">
        <img 
          src={imageUrl}
          className="w-full h-full object-cover opacity-40"
          alt={title}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-stone-950/70 via-transparent to-stone-950"></div>
      </div>

      <div className="relative z-10 text-center px-6 max-w-4xl">
        <div className="space-y-4 animate-fadeInUp">
          <span className="text-white text-base md:text-lg uppercase tracking-[0.6em] font-light opacity-90 block leading-none">
            {subtitle}
          </span>
          <h1 className="text-5xl md:text-7xl text-white font-bold leading-[1.1] tracking-tighter">
            {title.split(' ').map((word, idx, arr) => 
              idx === arr.length - 1 ? 
                <span key={idx} className="font-serif italic text-white/80">{word}</span> 
                : <span key={idx}>{word} </span>
            )}
          </h1>
          <p className="text-stone-300 text-lg md:text-xl max-w-2xl mx-auto font-light italic leading-relaxed opacity-80">
            {description}
          </p>
        </div>
      </div>
    </section>
  );
};

export default PageHeader;
