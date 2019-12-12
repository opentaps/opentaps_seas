/*
# This file is part of opentaps Smart Energy Applications Suite (SEAS).

# opentaps Smart Energy Applications Suite (SEAS) is free software:
# you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# opentaps Smart Energy Applications Suite (SEAS) is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with opentaps Smart Energy Applications Suite (SEAS).
# If not, see <https://www.gnu.org/licenses/>.
*/
/* Project specific Vue Components and code goes here. */
function saveTextAsCsvFile(filename, data) {
  var blob = new Blob([
                        new Uint8Array([0xEF, 0xBB, 0xBF]), // UTF-8 BOM
                        data
                      ],
                      {type: 'text/csv;charset=utf-8;'});
  if (window.navigator.msSaveOrOpenBlob) {
    window.navigator.msSaveBlob(blob, filename);
  }
  else{
    var elem = window.document.createElement('a');
    elem.href = window.URL.createObjectURL(blob);
    elem.download = filename;
    document.body.appendChild(elem);
    elem.click();
    document.body.removeChild(elem);
  }
}

/* use This method to parse dates from the server, this also removes the local timezone offset
so that if the date was 2011-06-21 10:00:00 it displays the exact same time in the browser */
function parse_date(s) {
  // eg: s = '2011-06-21T14:27:28.593Z';
  var a = s.split(/[^0-9]/);
  if (a.length < 3) throw ("Invalid date");
  var h = 0, m = 0, s = 0;
  if (a.length >= 4) h = a[3];
  if (a.length >= 5) m = a[4];
  if (a.length >= 6) s = a[5];

  d = new Date (a[0],a[1]-1,a[2],a[3],a[4],a[5] );
  return d;
}

function getResponseError(err) {
  console.log('getResponseError: ', err);
  if (!err) return {};
  errors = err;
  if (err.response && err.response.errors) errors = err.response.errors;
  else if (err.errors) errors = err.errors;
  console.error('getResponseError err = ', errors);
  if (typeof errors === 'string') {
    console.error('getResponseError return string err = ', errors);
    return {error: errors};
  }
  if (err.response && err.response.statusText) {
    console.error('getResponseError response statusText err = ', err.response.statusText);
    return {error: err.response.statusText};
  }
  if (err.message) {
    console.error('getResponseError message err = ', err.message);
    return {error: err.message};
  }
  console.error('getResponseError return raw error');
  return err;
}

function wait_p(ms) {
  return (x) => new Promise(resolve => setTimeout(() => resolve(x), ms ? ms : 1000))
}

function wait(ms) {
  return wait_p(ms)()
}

var eventHub = new Vue();

Vue.use(VuejsDialog.main.default, {
  okText: 'Proceed',
  cancelText: 'Cancel',
  loader: true
});

Vue.component('vue-bootstrap-typeahead', VueBootstrapTypeahead)
Vue.component('v-select', VueSelect.VueSelect)

Vue.component('tag-value-input', {
  delimiters: ['$[', ']'],
  template: `
  <div class="form-group" v-if="tag_needs_value(selectedTag)">
    <label v-if="!noLabel" for="valueInput">$[ selectedTag.kind ] - $[ selectedTag.description ]</label>
    <input v-if="!can_suggest(selectedTag)"
      :class="{'form-control':1, 'is-invalid': errors}"
      id="valueInput"
      name="value"
      v-bind:value="internal_value"
      v-on:input="$emit('input', $event.target.value)"
      placeholder="Value..."
      required="required"></input>
    <vue-bootstrap-typeahead
      v-if="can_suggest(selectedTag)"
      :input-class="'form-control' + (errors ? ' is-invalid' : '')"
      :serializer="s => s.object_id || s.entity_id"
      id="valueInput"
      ref="valueInput"
      :min-matching-chars="0"
      name="value"
      v-model="internal_value"
      v-on:input="$emit('input', $event)"
      :data="valid_tag_values"
      placeholder="Value...">
      <template slot="suggestion" slot-scope="{ data, htmlText }">
        <span v-html="htmlText"></span>&nbsp;<small>$[ display_suggestion(data) ]</small>
      </template>
    </vue-bootstrap-typeahead>
    <span v-for="err in errors" class="text-danger">$[ err ]</span>
  </div>
  `,
  props: {
    csrfmiddlewaretoken: String,
    selectedTag: Object,
    value: String,
    errors: Array,
    noLabel: Boolean
  },
  data() {
    return {
      valid_tag_values: [],
      internal_value: this.value,
    }
  },
  mounted() {
    this.get_valid_tag_values(this.selectedTag)
    if (this.$refs.valueInput) {
      this.$refs.valueInput.inputValue = this.internal_value
    }
  },
  watch: {
    selectedTag: function (val) {
      this.get_valid_tag_values(val)
      if (this.$refs.valueInput) {
        this.$refs.valueInput.inputValue = this.internal_value
      }
    },
  },
  methods:{
    tag_needs_value(item) {
      return (item && item.kind && item.kind != 'Marker')
    },
    can_suggest(item) {
      return (item && item.tag && ['modelRef', 'siteRef', 'equipRef'].includes(item.tag))
    },
    get_valid_tag_values(item) {
      if (!item || !item.tag) return this.valid_tag_values = []
      url = null
      if ('modelRef' == item.tag) url = dutils.urls.resolve('model_list_json')
      if ('siteRef' == item.tag) url = dutils.urls.resolve('site_list_json')
      if ('equipRef' == item.tag) url = dutils.urls.resolve('equipment_list_json')
      if (!url) return this.valid_tag_values = []
      axios.get(url)
        .then(x => this.valid_tag_values = x.data.items)
        .catch(err => {
          console.error('loading valid_tag_values error :', err);
        });
    },
    display_suggestion(item) {
      t = []
      if ('siteRef' == this.selectedTag.tag) {
        if (item.description) t.push(item.description);
        if (item.state) t.push(item.state);
        if (item.city) t.push(item.city);
      } else {
        if (item.description) t.push(item.description);
      }
      if (t.length) return t.join(' ')
      return null
    }
  }
});


Vue.component('tag-edit', {
  delimiters: ['$[', ']'],
  template: `
  <div scope="row" class="row align-items-start justify-content-between ftable-row">
    <div class="col-8 col-lg-auto text-nowrap m-0">
      <span v-if="!get_link(item)"><i v-if="!item.found" class="fa fa-times"></i> $[display_tag(item)]</span>
      <a v-if="get_link(item)" :href="get_link(item)"><i v-if="!item.found" class="fa fa-times"></i> $[display_tag(item)]</a>
    </div>
    <div class="buttons col-auto row text-nowrap m-0 pr-0">
      <button v-if="can_edit(item)" v-on:click="edit_tag()" class="btn btn-outline-primary btn-sm"><i class="fas fa-edit"></i></button>
      <button v-if="can_delete(item)" v-confirm="set_confirm()" class="btn btn-outline-danger btn-sm  ml-1"><i class="fas fa-trash"></i></button>
    </div>
  </div>
  `,
  props: {
    url: String,
    csrfmiddlewaretoken: String,
    tag: Object,
  },
  data() {
    return {
      item: {
          tag: this.tag.tag,
          kind: this.tag.kind,
          description: this.tag.description,
          value: this.tag.value,
          found: this.tag.found,
          slug: this.tag.slug,
          ref: this.tag.ref,
          __title: this.tag.description,
          __details: this.tag.details || this.tag.description,
          __nolabels: true
        }
    }
  },
  created() {
    eventHub.$on('tag_changed', x => {
      console.log('tag_changed', x)
      if (x.item.tag == this.item.tag) {
        if (x.type == 'deleted') {
          this.item.value = null
          this.item.found = false
          this.item.ref = null
        } else {
          this.item.value = x.item.value
          this.item.ref = x.item.ref
          this.item.found = true
        }
      }
    })
  },
  watch: {
  },
  methods:{
    display_tag(tag) {
      console.log('display_tag', tag)
      if (tag.kind == 'Marker') {
        return (tag.found ? '✓ ' : '') + tag.description
      }
      return tag.description + ': ' + this.get_tag_value(tag)
    },
    get_tag_value(tag) {
      if (tag.tag == 'modelRef' && tag.ref) {
        return tag.value
      }
      return (tag.value ? tag.value : 'n/a')
    },
    get_link(tag) {
      return dutils.urls.resolve_tag_linked_value(tag)
    },
    can_edit(tag) {
      return !tag.found || 'Marker' != tag.kind
    },
    can_delete(tag) {
      return tag.found
    },
    set_confirm() {
      return {
        okText: 'Delete',
        ok: dialog => this.delete_cb(dialog),
        message: 'Are you sure?'
      }
    },
    delete_cb(dialog) {
      this.delete_item(this.item).then(() => dialog.close())
    },
    delete_item(item) {
      console.log('delete_item', item)
      const formData = new FormData()
      formData.set('csrfmiddlewaretoken', this.csrfmiddlewaretoken)
      formData.set('delete', 1)
      if (item.kind != 'Marker') {
        formData.set('value', 1)
      }
      formData.set('tag', item.tag)
      return axios.post(this.url, formData)
          .then(x => x.data)
          .then(x => {
            console.log('delete_item Done', item)
            if (x.success) {
              this.item.found = false
              eventHub.$emit('tag_changed', {type: 'deleted', item: item})
              return x
            } else {
              return Promise.reject(x.errors)
            }
          })
          .catch(err => { console.error('delete error :', err) });
    },
    edit_tag() {
      eventHub.$emit('showModal_tag', this.item)
    },
  }
});

Vue.component('form-modal', {
  delimiters: ['$[', ']'],
  template: `
  <transition name="modal" v-if="visible">
    <div class="form-modal modal-mask">
      <div class="modal-wrapper">
        <div class="modal-container">

          <div class="modal-header" v-if="!item.__title">$[ title ] $[ title_name ]</div>
          <div class="modal-header" v-if="item.__title">$[ item.__title ]</div>

          <div class="modal-body">

            <div class="alert alert-danger" role="alert" v-if="errors.error">
              $[ errors.error ]
            </div>

            <p v-if="item.__details">$[ item.__details ]</p>

            <p class="text-muted" v-if="item.kind == 'Marker'">Set the $[ item.tag ] marker tag.</p>

            <div class="form-group" v-for="(field, idx) in fields">
              <label v-if="!item.__nolabels && field.label" :for="field.key">$[ field.label ]</label>
              <textarea v-if="field.type == 'textarea'" :class="{'form-control':1, 'is-invalid': errors[field.key]}" :id="field.key" :name="field.key" rows="3" v-model="field.value" :placeholder="field.placeholder"></textarea>
              <input v-if="field.type == 'input'" :class="{'form-control':1, 'is-invalid': errors[field.key]}" :id="field.key" :name="field.key" v-model="field.value" :placeholder="field.placeholder"></input>
              <input v-if="field.type == 'file'" type="file" :class="{'form-control':1, 'is-invalid': errors[field.key]}" :id="field.key" :name="field.key" :placeholder="field.placeholder" @change="filesChange(field, $event.target.name, $event.target.files)"></input>
              <div v-if="!item.__nolabels && field.type == 'display'">$[ field.value ]</div>
              <div v-if="field.type == 'tag'">
              <tag-value-input
                :csrfmiddlewaretoken="csrfmiddlewaretoken"
                :selected-tag="field.selectedTag"
                v-model="field.value"
                :no-label="item.__nolabels"></tag-value-input>
              </div>
              <span v-for="err in errors[field.key]" class="text-danger">$[ err ]</span>
            </div>

          </div>

          <div class="modal-footer">
            <button class="modal-default-button btn btn-outline-danger" @click="closeModal">Cancel</button>
            <button class="modal-default-button btn btn-outline-primary" @click="save">$[ save_label(item) ]</button>
          </div>
        </div>
      </div>
    </div>
  </transition>
  `,
  props: {
    url: {
      type: String,
      required: true
    },
    title: {
      type: String,
      default: 'Edit'
    },
    csrfmiddlewaretoken: String
  },
  data() {
    return {
      title_name: null,
      item: null,
      errors: {},
      visible: false,
    }
  },
  methods:{
    showModal: function(item){
      console.log('showModal', item)
      this.item = item
      this.visible = true
      this.errors = {}
      this.post_show(item)
    },
    post_show: function(item) {
      /* placeholder */
    },
    closeModal: function(){
      this.visible = false
      this.item = null
      this.errors = {}
    },
    filesChange(field, fieldName, fileList) {
      console.log('filesChange', field, fieldName, fileList)
      if (!fileList.length) return;
      field.value = fileList[0]
    },
    pre_save: function(formData) {
      /* placeholder */
    },
    post_save: function(response) {
      /* placeholder */
    },
    save_label: function(item) {
      if (item && item.kind && item.kind == 'Marker') return 'Set Tag'
      return 'Save'
    },
    save: function(){
      console.log('save', this.item)
      const formData = new FormData()
      formData.set('csrfmiddlewaretoken', this.csrfmiddlewaretoken)
      formData.set('id', this.item.id)
      formData.set('update', 1)
      this.pre_save(formData, this.item)
      axios.post(this.url, formData, {validateStatus: status => status < 500})
          // get data
          .then(x => x.data)
          .then(x => {
            if (x.success) {
              this.post_save(x)
              this.closeModal()
              return x
            } else {
              return Promise.reject(x.errors)
            }
          })
          .catch(err => {
            e = getResponseError(err)
            console.error(e, err)
            this.errors = e
          });
    }
  }
});

const STATUS_INITIAL = 0, STATUS_SAVING = 1

Vue.component('my-datetime', {
  delimiters: ['$[', ']'],
  props: {
    value: String,
  },
  template: `
    <span class="text-muted">$[ fmtdate(value) ]</span>
  `,
  methods: {
    fmtdate(dateString) {
      if (!dateString) return null
      return moment(dateString).local().format('lll')
    }
  }
});

Vue.component('base-list-form', {
  delimiters: ['$[', ']'],
  props: {

  },
  data() {
    return {
      url: null,
      csrfmiddlewaretoken: null,
      items: [],
      errors: {},
      currentStatus: null,
    }
  },
  created: function() {
    this.reload()
  },
  mounted() {
    this.reset()
  },
  computed: {
    isInitial() {
      return this.currentStatus === STATUS_INITIAL
    },
    isSaving() {
      return this.currentStatus === STATUS_SAVING
    },
  },
  methods: {
    reset() {
      /* placeholder */
      this._reset()
    },
    _reset() {
      // reset form to initial state
      this.currentStatus = STATUS_INITIAL
      this.errors = {}
    },
    reload() {
      /* placeholder */
    },
    reload_items() {
      if (this.url) {
        axios.get(this.url)
          .then(x => this.items = x.data.items)
          .catch(err => {
            console.error('loading items error :', err);
          });
      }
    },
    set_confirm(idx) {
      return {
        okText: 'Delete',
        ok: dialog => this.delete_cb(dialog, idx),
        message: 'Are you sure?'
      }
    },
    delete_cb(dialog, idx) {
      item = this.items[idx];
      this.delete_item(item, idx).then(() => dialog.close())
    },
    pre_delete: function(formData, item, idx) {
      /* placeholder */
    },
    post_delete: function(item) {
      /* placeholder */
    },
    delete_item(item, idx) {
      console.log('delete_item', item)
      const formData = new FormData()
      formData.set('csrfmiddlewaretoken', this.csrfmiddlewaretoken)
      formData.set('delete', 1)
      this.pre_delete(formData, item, idx)
      return axios.post(this.url, formData)
          .then(x => x.data)
          .then(x => {
            console.log('delete_item Done', item)
            if (x.success) {
              this.$delete(this.items, idx)
              this.post_delete(item)
              return x
            } else {
              return Promise.reject(x.errors)
            }
          })
          .catch(err => { console.error('delete error :', err) });
    },
    pre_save: function(formData) {
      /* placeholder */
    },
    post_save(item) {
      /* placeholder */
      console.log('Saved item: ', item)
      this.items.push(item)
    },
    send(formData, url) {
      r = this.pre_save(formData)
      if (r) return r;
      formData.set('csrfmiddlewaretoken', this.csrfmiddlewaretoken);
      return axios.post(url ? url : this.url, formData, {validateStatus: status => status < 500})
          // get data
          .then(x => x.data)
          .then(x => {
            if (x.success) {
              return x.results
            } else {
              return Promise.reject(x.errors)
            }
          })
    },
    save() {
      this.errors = {}
      this.currentStatus = STATUS_SAVING

      const formData = new FormData()

      this.send(formData)
        .then(x => {
          x.map(this.post_save)
          this.reset()
        })
        .catch(err => {
          this.errors = getResponseError(err)
          console.error(this.errors, err)
          this.currentStatus = STATUS_INITIAL
        });
    },
    fmtdate(dateString) {
      if (!dateString) return null
      return moment(dateString).local().format('lll')
    }
  }
});

