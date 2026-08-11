/// <reference types="google.maps" />
import React, { useEffect, useRef } from 'react';

interface Coordinate {
  lat: number;
  lng: number;
}

interface Intersection {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
}

interface Road {
  id: string;
  name: string;
  start_node: string;
  end_node: string;
  length_meters: number;
  capacity: number;
  speed_limit_kmh: number;
  road_type: string;
  availability: number;
  current_volume: number;
  criticality: number;
  path?: Coordinate[];
}

interface Facility {
  id: string;
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  nearest_node: string;
}

interface PopulationZone {
  id: string;
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  population: number;
  nearest_node: string;
}

interface RoadNetworkMapProps {
  roads: Road[];
  intersections: Intersection[];
  facilities: Facility[];
  populationZones: PopulationZone[];

  selectedRoad: Road | null;
  selectedIntersection: Intersection | null;
  selectedFacility: Facility | null;
  selectedZone: PopulationZone | null;

  onSelectRoad: (road: Road) => void;
  onSelectIntersection: (node: Intersection) => void;
  onSelectFacility: (facility: Facility) => void;
  onSelectZone: (zone: PopulationZone) => void;

  thresholds: { clear: number; moderate: number };
}

export const RoadNetworkMap: React.FC<RoadNetworkMapProps> = ({
  roads,
  intersections,
  facilities,
  populationZones,
  selectedRoad,
  selectedIntersection,
  selectedFacility,
  selectedZone,
  onSelectRoad,
  onSelectIntersection,
  onSelectFacility,
  onSelectZone,
  thresholds
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<google.maps.Map | null>(null);

  // Keep track of rendered overlays to update or delete them in-place
  const polylinesRef = useRef<Record<string, google.maps.Polyline>>({});
  const intersectionCirclesRef = useRef<Record<string, google.maps.Circle>>({});
  const facilityMarkersRef = useRef<Record<string, google.maps.Marker>>({});
  const zoneCirclesRef = useRef<Record<string, google.maps.Circle>>({});

  // Sync callbacks via refs to avoid re-running effects when handlers change
  const handlersRef = useRef({
    onSelectRoad,
    onSelectIntersection,
    onSelectFacility,
    onSelectZone
  });

  useEffect(() => {
    handlersRef.current = {
      onSelectRoad,
      onSelectIntersection,
      onSelectFacility,
      onSelectZone
    };
  }, [onSelectRoad, onSelectIntersection, onSelectFacility, onSelectZone]);

  // Initialize Map

  useEffect(() => {
    if (!mapRef.current) return;

    const map = new google.maps.Map(mapRef.current, {
      center: { lat: 16.5062, lng: 80.6480 },
      zoom: 14,
      styles: [
        {
          featureType: 'poi',
          elementType: 'labels',
          stylers: [{ visibility: 'off' }]
        },
        {
          featureType: 'transit',
          elementType: 'labels',
          stylers: [{ visibility: 'off' }]
        }
      ]
    });

    mapInstanceRef.current = map;

    // Cleanup overlays on unmount
    return () => {
      Object.values(polylinesRef.current).forEach(poly => poly.setMap(null));
      Object.values(intersectionCirclesRef.current).forEach(c => c.setMap(null));
      Object.values(facilityMarkersRef.current).forEach(m => m.setMap(null));
      Object.values(zoneCirclesRef.current).forEach(c => c.setMap(null));

      polylinesRef.current = {};
      intersectionCirclesRef.current = {};
      facilityMarkersRef.current = {};
      zoneCirclesRef.current = {};
    };
  }, []);

  // Update Roads (Polylines)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Helper to determine road color based on congestion
    const getCongestionColor = (road: Road) => {
      if (road.availability === 0) return '#64748b'; // Gray for closed
      const ratio = road.current_volume / road.capacity;
      if (ratio <= thresholds.clear) return '#10b981'; // Green
      if (ratio <= thresholds.moderate) return '#f59e0b'; // Amber
      return '#f43f5e'; // Red
    };

    const currentPolylines = polylinesRef.current;
    const roadIds = new Set<string>();

    roads.forEach(road => {
      if (!road.path || road.path.length === 0) return;
      roadIds.add(road.id);

      const color = getCongestionColor(road);
      const isSelected = selectedRoad?.id === road.id;
      const weight = isSelected ? 8 : 4;
      const opacity = isSelected ? 0.95 : 0.75;

      let polyline = currentPolylines[road.id];

      if (!polyline) {
        polyline = new google.maps.Polyline({
          path: road.path,
          geodesic: true,
          strokeColor: color,
          strokeOpacity: opacity,
          strokeWeight: weight,
          map: map,
          zIndex: isSelected ? 100 : 10
        });

        polyline.addListener('click', () => {
          handlersRef.current.onSelectRoad(road);
        });

        currentPolylines[road.id] = polyline;
      } else {
        polyline.setOptions({
          strokeColor: color,
          strokeOpacity: opacity,
          strokeWeight: weight,
          zIndex: isSelected ? 100 : 10
        });
      }
    });

    // Clean up removed roads
    Object.keys(currentPolylines).forEach(roadId => {
      if (!roadIds.has(roadId)) {
        currentPolylines[roadId].setMap(null);
        delete currentPolylines[roadId];
      }
    });
  }, [roads, selectedRoad, thresholds]);

  // Update Intersections (Circles)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const currentCircles = intersectionCirclesRef.current;
    const nodeIds = new Set<string>();

    intersections.forEach(node => {
      nodeIds.add(node.id);

      const isSelected = selectedIntersection?.id === node.id;
      const isBlockedNode = roads.some(
        r => r.availability === 0 && (r.start_node === node.id || r.end_node === node.id)
      );

      const strokeColor = isSelected ? '#38bdf8' : isBlockedNode ? '#f43f5e' : '#94a3b8';
      const strokeWeight = isSelected ? 3 : 1;
      const radius = isSelected ? 35 : isBlockedNode ? 25 : 15; // in meters

      let circle = currentCircles[node.id];

      if (!circle) {
        circle = new google.maps.Circle({
          center: { lat: node.latitude, lng: node.longitude },
          radius: radius,
          fillColor: isBlockedNode ? '#f43f5e' : '#1e293b',
          fillOpacity: 0.6,
          strokeColor: strokeColor,
          strokeOpacity: 0.8,
          strokeWeight: strokeWeight,
          map: map,
          zIndex: isSelected ? 50 : 20
        });

        circle.addListener('click', () => {
          handlersRef.current.onSelectIntersection(node);
        });

        currentCircles[node.id] = circle;
      } else {
        circle.setOptions({
          radius: radius,
          fillColor: isBlockedNode ? '#f43f5e' : '#1e293b',
          strokeColor: strokeColor,
          strokeWeight: strokeWeight,
          zIndex: isSelected ? 50 : 20
        });
      }
    });

    // Clean up removed intersections
    Object.keys(currentCircles).forEach(nodeId => {
      if (!nodeIds.has(nodeId)) {
        currentCircles[nodeId].setMap(null);
        delete currentCircles[nodeId];
      }
    });
  }, [intersections, selectedIntersection, roads]);

  // Update Facilities (Markers)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const currentMarkers = facilityMarkersRef.current;
    const facIds = new Set<string>();

    facilities.forEach(facility => {
      facIds.add(facility.id);

      let marker = currentMarkers[facility.id];
      const isSelected = selectedFacility?.id === facility.id;

      if (!marker) {
        const emoji = facility.type === 'HOSPITAL' ? '🏥' : facility.type === 'FIRE_STATION' ? '🔥' : '👮';
        marker = new google.maps.Marker({
          position: { lat: facility.latitude, lng: facility.longitude },
          map: map,
          title: facility.name,
          label: {
            text: emoji,
            fontSize: isSelected ? '20px' : '14px'
          },
          animation: isSelected ? google.maps.Animation.BOUNCE : null
        });

        marker.addListener('click', () => {
          handlersRef.current.onSelectFacility(facility);
        });

        currentMarkers[facility.id] = marker;
      } else {
        const currentLabel = marker.getLabel();

        marker.setOptions({
          label: {
            text: typeof currentLabel === 'string'
              ? currentLabel
              : currentLabel?.text || '',
            fontSize: isSelected ? '20px' : '14px'
          },
          animation: isSelected ? google.maps.Animation.BOUNCE : null
        });
      }
    });

    // Clean up removed facilities
    Object.keys(currentMarkers).forEach(facId => {
      if (!facIds.has(facId)) {
        currentMarkers[facId].setMap(null);
        delete currentMarkers[facId];
      }
    });
  }, [facilities, selectedFacility]);

  // Update Population Zones (Large circles)
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const currentZones = zoneCirclesRef.current;
    const zoneIds = new Set<string>();

    populationZones.forEach(zone => {
      zoneIds.add(zone.id);

      let circle = currentZones[zone.id];
      const isSelected = selectedZone?.id === zone.id;
      const color = zone.type === 'COMMERCIAL' ? '#38bdf8' : '#10b981';

      if (!circle) {
        circle = new google.maps.Circle({
          center: { lat: zone.latitude, lng: zone.longitude },
          radius: zone.radius_meters || 400,
          fillColor: color,
          fillOpacity: isSelected ? 0.25 : 0.05,
          strokeColor: color,
          strokeOpacity: isSelected ? 0.6 : 0.15,
          strokeWeight: isSelected ? 3 : 1,
          map: map,
          zIndex: isSelected ? 15 : 5
        });

        circle.addListener('click', () => {
          handlersRef.current.onSelectZone(zone);
        });

        currentZones[zone.id] = circle;
      } else {
        circle.setOptions({
          fillOpacity: isSelected ? 0.25 : 0.05,
          strokeOpacity: isSelected ? 0.6 : 0.15,
          strokeWeight: isSelected ? 3 : 1,
          zIndex: isSelected ? 15 : 5
        });
      }
    });

    // Clean up removed zones
    Object.keys(currentZones).forEach(zoneId => {
      if (!zoneIds.has(zoneId)) {
        currentZones[zoneId].setMap(null);
        delete currentZones[zoneId];
      }
    });
  }, [populationZones, selectedZone]);

  return (
    <div
      ref={mapRef}
      className="google-map-container"
      style={{ width: '100%', height: '100%', borderRadius: 'inherit' }}
    />
  );
};
