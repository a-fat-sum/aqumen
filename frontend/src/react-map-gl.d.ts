declare module 'react-map-gl' {
    import * as React from 'react';

    export interface ViewState {
        longitude: number;
        latitude: number;
        zoom: number;
        pitch: number;
        bearing: number;
    }

    export interface ViewStateChangeEvent {
        viewState: ViewState;
    }

    export interface MapLayerMouseEvent {
        lngLat: { lng: number; lat: number };
    }

    export interface MapProps extends React.HTMLAttributes<HTMLDivElement> {
        mapboxAccessToken?: string;
        mapStyle?: string;
        longitude?: number;
        latitude?: number;
        zoom?: number;
        onMove?: (e: ViewStateChangeEvent) => void;
        onClick?: (e: MapLayerMouseEvent) => void;
        cursor?: string;
        style?: React.CSSProperties;
        children?: React.ReactNode;
    }

    export default class Map extends React.Component<MapProps> { }

    export interface MarkerProps {
        longitude: number;
        latitude: number;
        anchor?: string;
        children?: React.ReactNode;
    }

    export class Marker extends React.Component<MarkerProps> { }
}
