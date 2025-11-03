import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.tamaletown.app',    // CHANGE ME
  appName: 'Tamale Town U.S.A.',
  webDir: 'dist',
  bundledWebRuntime: false,
  server: {
    androidScheme: 'https',
    cleartext: false
  },
  ios: {
    contentInset: 'automatic',
    allowsLinkPreview: true
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#101012',
      androidScaleType: 'CENTER_CROP',
      showSpinner: false
    }
  }
};

export default config;
