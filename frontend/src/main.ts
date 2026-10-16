import { mount } from 'svelte';
import App from './App.svelte';
import './app.css';

const ziel = document.getElementById('app');
if (ziel) mount(App, { target: ziel });
