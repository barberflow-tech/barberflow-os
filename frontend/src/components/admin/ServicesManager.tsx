import React, { useState } from 'react'
import { useServicesStore } from '../../stores/useServicesStore'
import type { Service } from '../../stores/useServicesStore'

type ServiceFormData = Omit<Service, 'id'>

const initialFormData: ServiceFormData = {
  name: '',
  duration_minutes: 30,
  price: 0,
  category: 'Cortes',
  is_active: true,
  is_featured: false,
  image_url: '',
}

export const ServicesManager: React.FC = () => {
  const { services, updateServiceOptimistic, deleteService } = useServicesStore()

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingService, setEditingService] = useState<Service | null>(null)

  const [serviceToDelete, setServiceToDelete] = useState<Service | null>(null)

  const [selectedCategory, setSelectedCategory] = useState('Todas')

  const [formData, setFormData] = useState<ServiceFormData>({ ...initialFormData })

  const [imagePreview, setImagePreview] = useState('')

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const target = e.target
    const { name, type } = target

    let value: string | number | boolean

    if (type === 'checkbox') {
      value = (target as HTMLInputElement).checked
    } else if (name === 'price' || name === 'duration_minutes') {
      value = Number(target.value)
    } else {
      value = target.value
    }

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]

    if (!file) return

    if (!file.type.startsWith('image/')) {
      alert('Por favor, selecciona un archivo de imagen.')
      e.target.value = ''
      return
    }

    const reader = new FileReader()

    reader.onload = () => {
      const imageData = reader.result as string

      setImagePreview(imageData)

      setFormData((prev) => ({
        ...prev,
        image_url: imageData,
      }))
    }

    reader.onerror = () => {
      alert('No se pudo cargar la imagen.')
    }

    reader.readAsDataURL(file)
  }

  const resetForm = () => {
    setFormData({ ...initialFormData })
    setEditingService(null)
    setImagePreview('')
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()

    if (!editingService) return

    updateServiceOptimistic(editingService.id, formData)

    setIsModalOpen(false)
    resetForm()
  }

  const handleEditClick = (service: Service) => {
    setEditingService(service)

    setFormData({
      name: service.name,
      duration_minutes: service.duration_minutes,
      price: service.price,
      category: service.category,
      is_active: service.is_active,
      is_featured: service.is_featured,
      image_url: service.image_url,
    })

    setImagePreview(service.image_url)
    setIsModalOpen(true)
  }

  const handleDelete = (service: Service) => {
    setServiceToDelete(service)
  }

  const confirmDelete = () => {
    if (!serviceToDelete) return

    deleteService(serviceToDelete.id)
    setServiceToDelete(null)
  }

  const filteredServices =
    selectedCategory === 'Todas'
      ? services
      : selectedCategory === 'Destacados'
        ? services.filter((service) => service.is_featured)
        : services.filter((service) => service.category === selectedCategory)

  const categories = [
    'Todas',
    'Cortes',
    'Barbas',
    'Tratamientos',
    'Combos',
    'Destacados',
  ]

  return (
    <div className="w-full max-w-7xl mx-auto p-6 space-y-6 bg-slate-50 dark:bg-gray-950 min-h-screen">
      {/* Encabezado */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center bg-white dark:bg-gray-900 p-6 rounded-3xl shadow-sm border border-slate-200 dark:border-gray-800 gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tight">
            Catálogo de Servicios
          </h1>

          <p className="text-xs text-slate-500 mt-1">
            Administra precios, tiempos de atención, estados y servicios destacados.
          </p>
        </div>

        <span className="text-xs font-bold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-gray-800 px-3 py-2 rounded-xl">
          {services.length} servicios registrados
        </span>
      </div>

      {/* Filtros */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white dark:bg-gray-900 p-4 rounded-3xl border border-slate-200 dark:border-gray-800 shadow-sm">
        <div className="flex gap-2 overflow-x-auto pb-1 w-full sm:w-auto">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`px-4 py-2 rounded-xl text-xs font-bold cursor-pointer transition-all ${
                selectedCategory === category
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm'
                  : 'bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200'
              }`}
            >
              {category === 'Destacados' ? '⭐ ' : ''}
              {category}
            </button>
          ))}
        </div>

        <div className="text-xs text-slate-400 font-medium whitespace-nowrap">
          Mostrando:{' '}
          <span className="text-slate-700 dark:text-slate-200 font-bold">
            {filteredServices.length} elementos
          </span>
        </div>
      </div>

      {/* Tarjetas de servicios */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {filteredServices.map((service) => (
          <div
            key={service.id}
            className="group relative bg-white dark:bg-gray-900 rounded-3xl border border-slate-200 dark:border-gray-800 overflow-hidden shadow-sm hover:shadow-md transition-all flex flex-col justify-between"
          >
            {/* Imagen */}
            <div className="relative h-48 bg-slate-100 dark:bg-gray-800">
              <img
                src={service.image_url}
                alt={service.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                }}
              />

              {/* Favoritos */}
              <button
                onClick={() =>
                  updateServiceOptimistic(service.id, {
                    is_featured: !service.is_featured,
                  })
                }
                className={`absolute top-3 left-3 w-9 h-9 rounded-full flex items-center justify-center shadow-md cursor-pointer transition-transform hover:scale-110 ${
                  service.is_featured
                    ? 'bg-amber-400 text-white'
                    : 'bg-white/90 text-slate-400'
                }`}
                title={
                  service.is_featured ? 'Quitar de destacados' : 'Marcar como destacado'
                }
              >
                ★
              </button>

              {/* Editar y eliminar */}
              <div className="absolute top-3 right-3 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <button
                  onClick={() => handleEditClick(service)}
                  className="w-9 h-9 rounded-full bg-white/90 text-slate-700 flex items-center justify-center shadow-md hover:bg-white transition-transform hover:scale-105"
                  title="Editar servicio"
                >
                  ✏️
                </button>

                <button
                  onClick={() => handleDelete(service)}
                  className="w-9 h-9 rounded-full bg-red-600 text-white flex items-center justify-center shadow-md hover:bg-red-700 transition-transform hover:scale-105"
                  title="Eliminar servicio"
                >
                  🗑
                </button>
              </div>

              {/* Categoría */}
              <div className="absolute bottom-3 left-3">
                <span className="text-[10px] font-extrabold px-2.5 py-1 rounded-lg bg-black/60 backdrop-blur-md text-white uppercase tracking-wider">
                  {service.category}
                </span>
              </div>
            </div>

            {/* Información */}
            <div className="p-4 flex flex-col justify-between flex-grow space-y-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white line-clamp-1">
                  {service.name}
                </h3>

                <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                  <span>⏱️ {service.duration_minutes} min</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-gray-800">
                <span className="text-base font-black text-slate-900 dark:text-white">
                  ${service.price.toLocaleString('es-CO')}
                </span>

                <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400">
                  Activo
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modal de edición */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-3xl max-w-md w-full max-h-[90vh] overflow-y-auto p-6 shadow-xl border border-slate-200 dark:border-gray-800 space-y-4">
            <h2 className="text-lg font-black text-slate-900 dark:text-white">
              Editar Servicio
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Nombre */}
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Nombre del Servicio
                </label>

                <input
                  type="text"
                  name="name"
                  required
                  value={formData.name}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-800 text-slate-900 dark:text-white"
                  placeholder="Ej. Corte Fade"
                />
              </div>

              {/* Precio y duración */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Precio ($)
                  </label>

                  <input
                    type="number"
                    name="price"
                    required
                    min="0"
                    value={formData.price}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-800 text-slate-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Duración (min)
                  </label>

                  <input
                    type="number"
                    name="duration_minutes"
                    required
                    min="5"
                    step="5"
                    value={formData.duration_minutes}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-800 text-slate-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Categoría */}
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Categoría
                </label>

                <select
                  name="category"
                  value={formData.category}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-800 text-slate-900 dark:text-white"
                >
                  <option value="Cortes">Cortes</option>
                  <option value="Barbas">Barbas</option>
                  <option value="Tratamientos">Tratamientos</option>
                  <option value="Combos">Combos</option>
                </select>
              </div>

              {/* Imagen */}
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                  Imagen del servicio
                </label>

                <div className="relative overflow-hidden rounded-2xl border-2 border-dashed border-slate-300 dark:border-gray-700 bg-slate-50 dark:bg-gray-800">
                  {imagePreview ? (
                    <img
                      src={imagePreview}
                      alt="Vista previa del servicio"
                      className="w-full h-44 object-cover"
                    />
                  ) : (
                    <div className="h-44 flex flex-col items-center justify-center text-slate-400">
                      <span className="text-3xl mb-2">📷</span>
                      <span className="text-xs">Selecciona una imagen</span>
                    </div>
                  )}

                  <label className="flex items-center justify-center gap-2 p-3 bg-white dark:bg-gray-900 border-t border-slate-200 dark:border-gray-700 text-sm font-bold text-slate-700 dark:text-white cursor-pointer hover:bg-slate-100 dark:hover:bg-gray-800 transition-colors">
                    <span>📸</span>
                    Cambiar imagen
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleImageChange}
                      className="hidden"
                    />
                  </label>
                </div>

                <p className="text-[11px] text-slate-400 mt-2">
                  Formatos compatibles: JPG, PNG y WEBP.
                </p>
              </div>

              {/* Botones */}
              <div className="flex justify-end gap-2 pt-4 border-t border-slate-100 dark:border-gray-800">
                <button
                  type="button"
                  onClick={() => {
                    setIsModalOpen(false)
                    resetForm()
                  }}
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-slate-100 dark:bg-gray-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 transition-all"
                >
                  Cancelar
                </button>

                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm hover:opacity-90 transition-all"
                >
                  Guardar Cambios
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal personalizado de eliminación */}
      {serviceToDelete && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-service-title"
            className="w-full max-w-md rounded-3xl bg-white dark:bg-gray-900 p-6 shadow-2xl border border-slate-200 dark:border-gray-800"
          >
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 flex items-center justify-center rounded-full bg-red-100 dark:bg-red-950/50 text-red-600 dark:text-red-400 mb-4">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 9v4" />
                  <path d="M12 17h.01" />
                  <path d="M10.3 3.9 1.8 18.2a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
                </svg>
              </div>

              <h2
                id="delete-service-title"
                className="text-xl font-black text-slate-900 dark:text-white"
              >
                ¿Eliminar servicio?
              </h2>

              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Estás a punto de eliminar{' '}
                <span className="font-bold text-slate-800 dark:text-slate-200">
                  {serviceToDelete.name}
                </span>
                . Esta acción no se puede deshacer.
              </p>
            </div>

            <div className="flex gap-3 mt-8">
              <button
                type="button"
                onClick={() => setServiceToDelete(null)}
                className="flex-1 rounded-xl border border-slate-200 dark:border-gray-700 px-4 py-3 text-sm font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-gray-800 transition-colors"
              >
                Cancelar
              </button>

              <button
                type="button"
                onClick={confirmDelete}
                className="flex-1 rounded-xl bg-red-600 px-4 py-3 text-sm font-bold text-white hover:bg-red-700 shadow-sm transition-colors"
              >
                Sí, eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
