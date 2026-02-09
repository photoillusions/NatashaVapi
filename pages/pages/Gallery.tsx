import React from 'react';
import { Image as ImageIcon } from 'lucide-react';
import PageHeader from '../components/PageHeader';

const galleryImages = [
  'https://images.unsplash.com/photo-1519167758481-83f550bb49b3?auto=format&fit=crop&q=80&w=800',
  'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&q=80&w=800',
  'https://images.unsplash.com/photo-1519224052708-081b537129dd?auto=format&fit=crop&q=80&w=800',
  'https://images.unsplash.com/photo-1527529482837-4698179dc6ce?auto=format&fit=crop&q=80&w=800',
  'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&q=80&w=800',
  'https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&q=80&w=800',
];

const Gallery = () => {
  return (
    <>
      <PageHeader 
        subtitle="Visual Showcase"
        title="Event Gallery"
        description="Explore our collection of stunning celebrations and elegant events."
      />

      {/* Gallery Content */}
      <section className="py-56 bg-stone-50">
        <div className="max-w-[1600px] mx-auto px-8">
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

export default Gallery;
