import {makeAutoObservable} from 'mobx';
import type {Update} from 'history';
import {
  getCurrentPath,
  isMyLibraryRoute,
  isPublicCollectionsRoute,
} from 'js/router/routerUtils';
import {history} from 'js/router/historyRouter';

const DEFAULT_SEARCH_PHRASE = '';

type SearchBoxContextName = 'MY_LIBRARY' | 'PUBLIC_COLLECTIONS';

export const SEARCH_CONTEXTS: {
  [name in SearchBoxContextName]: SearchBoxContextName
} = {
  MY_LIBRARY: 'MY_LIBRARY',
  PUBLIC_COLLECTIONS: 'PUBLIC_COLLECTIONS',
};

export interface SearchBoxStoreData {
  context: SearchBoxContextName | null;
  searchPhrase: string;
}

class SearchBoxStore {
  previousPath = getCurrentPath();
  data: SearchBoxStoreData = {
    context: null,
    searchPhrase: DEFAULT_SEARCH_PHRASE,
  };

  constructor() {
    makeAutoObservable(this);
    history.listen(this.onRouteChange.bind(this));
    this.resetContext();
  }

  /** Manages clearing search when switching routes */
  onRouteChange(data: Update) {
    if (this.previousPath !== data.location.pathname) {
      this.clear();
    }
    this.previousPath = data.location.pathname;

    this.resetContext();
  }

  getSearchPhrase() {
    return this.data.searchPhrase;
  }

  setSearchPhrase(newVal: string) {
    if (this.data.searchPhrase !== newVal) {
      this.data.searchPhrase = newVal;
    }
  }

  getContext() {
    return this.data.context;
  }

  resetContext() {
    let newContext: SearchBoxContextName | null = null;

    if (isMyLibraryRoute()) {
      newContext = 'MY_LIBRARY';
    } else if (isPublicCollectionsRoute()) {
      newContext = 'PUBLIC_COLLECTIONS';
    }

    if (this.data.context !== newContext) {
      this.data.context = newContext;
      this.data.searchPhrase = DEFAULT_SEARCH_PHRASE;
    }
  }

  clear() {
    this.setSearchPhrase(DEFAULT_SEARCH_PHRASE);
  }
}

export default new SearchBoxStore;
