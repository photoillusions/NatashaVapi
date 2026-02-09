
import { Venue, Service } from './types';

export const VENUES: Venue[] = [
  {
    id: 'vault',
    name: 'The Vault Ballroom',
    location: 'Burlington, NJ',
    vibe: 'Historic Luxury',
    details: 'Housed in a bank building dating back to 1677, offering cobblestone charm and an unparalleled aesthetic.',
    features: [
      'Original walk-in bank vaults with 3-ton doors',
      'Manicured gardens with six-pillar runway',
      'Historic cast iron canopy'
    ],
    capacity: 'Main: 250 | Vault Room II: 100',
    advantage: 'Unique 5:00 AM alcohol license and rare historic architectural details.',
    pricing: 'Saturday rates from $3,795',
    image: '/images/venues/vault-ballroom.jpg'
  },
  {
    id: 'liberty',
    name: 'Mae’s Liberty Palace',
    location: 'Franklin Mills, Philadelphia',
    vibe: 'Mid-Market Powerhouse',
    details: 'A sophisticated 4,000 sq. ft. open-concept facility designed for versatility and regional accessibility.',
    features: [
      'Abundant natural light (perfect for showers)',
      'Outside patio for cocktail hours',
      'Ample free on-site parking'
    ],
    capacity: 'Up to 210 guests',
    advantage: 'Strategic location near I-95 and local hotels with superior parking availability.',
    pricing: 'Weekend sessions from $3,000',
    image: '/images/venues/liberty-palace.jpg'
  },
  {
    id: 'banquet',
    name: 'Natasha Mae’s Banquet Facility',
    location: 'Frankford, Philadelphia',
    vibe: 'The Urban Foundation',
    details: 'Cozy and elegant space optimized for high-utility and community accessibility in the heart of Frankford.',
    features: [
      'Designed to avoid "cavernous" feel',
      'Transit-oriented location',
      'Warm, intimate atmosphere'
    ],
    capacity: 'Up to 110 guests',
    advantage: 'Just 0.2 miles from SEPTA Church Station, unbeatable urban convenience.',
    pricing: 'Weekday rates from $1,000',
    image: '/images/venues/banquet-facility.jpg'
  }
];

export const SERVICES: Service[] = [
  {
    title: "Natasha’s Heavenly Designs",
    description: "Our creative backbone offering spectacular in-house floral and decor packages—from Harlem Nights/Gatsby to custom Marvel children's themes.",
    icon: "Flower"
  },
  {
    title: "Divine Dining",
    description: "In-house catering providing extensive menus including vegan and gluten-free options, maintaining the highest standards for every palate.",
    icon: "Utensils"
  },
  {
    title: "Personal Event Management",
    description: "Every occasion is guided by a dedicated Personal Event Manager, ensuring your vision is realized with professionalism and heart.",
    icon: "UserCheck"
  }
];
