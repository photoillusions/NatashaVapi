
import { Venue, Service } from './types';

export const VENUES: Venue[] = [
  {
    id: 'vault',
    name: 'The Vault Ballroom',
    location: 'Burlington, NJ',
    vibe: 'Historic Luxury',
    details: 'Our flagship historic-luxury destination. Housed in a bank building dating back to 1677, this venue offers unparalleled cobblestone charm and architectural authenticity that modern halls simply cannot replicate.',
    features: [
      'Original walk-in bank vaults with 3-ton doors (photo backdrop)',
      'Manicured gardens with six-pillar runway for outdoor ceremonies',
      'Historic cast stone columns and cast iron canopy',
      'Vault Room II: Intimate 100-guest top-floor space'
    ],
    capacity: 'Main Ballroom: 250 | Vault Room II: 100',
    advantage: 'Rare 5:00 AM alcohol license. One-of-a-kind historic aesthetic creates unforgettable destination events.',
    pricing: 'Saturday rates from $3,795',
    image: '/images/venues/vault-ballroom.jpg'
  },
  {
    id: 'liberty',
    name: 'Mae’s Liberty Palace',
    location: 'Franklin Mills, Philadelphia',
    vibe: 'Mid-Market Powerhouse',
    details: 'Our sophisticated mid-market solution. A versatile 4,000 sq. ft. open-concept facility positioned as a regional powerhouse for celebrations requiring premium space with superior accessibility.',
    features: [
      'Abundant natural light ideal for daytime showers and brunches',
      'Outside patio perfect for cocktail hours and outdoor ceremonies',
      'Ample free on-site parking (rare in Philadelphia area)',
      'Open floor plan for versatile layouts and thematic designs'
    ],
    capacity: 'Up to 210 guests',
    advantage: 'Strategic location near I-95 corridor and local hotels. Unmatched parking availability for regional guests.',
    pricing: 'Weekend from $3,000',
    image: '/images/venues/liberty-palace.jpg'
  },
  {
    id: 'banquet',
    name: 'Natasha Mae’s Banquet Facility',
    location: 'Frankford, Philadelphia',
    vibe: 'The Urban Foundation',
    details: 'Our high-frequency community hub. A cozy and elegant urban space specifically designed to avoid the "cavernous" feel, perfect for intimate local gatherings and neighborhood celebrations.',
    features: [
      'Intimate, warm atmosphere (50-110 guests)',
      'Premier transit-oriented accessibility',
      'Just 0.2 miles from SEPTA Church Station',
      'Affordable community rates with zero parking hassles'
    ],
    capacity: 'Up to 110 guests',
    advantage: 'Unbeatable urban convenience for local guests. Highest accessibility at the lowest investment.',
    pricing: 'Weekday from $1,000',
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
